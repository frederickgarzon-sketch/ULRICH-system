"""Ultralytics pose worker with primary-subject tracking and movement metrics."""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import torch
import cv2
from ultralytics import YOLO

from app.camera.camera_system import camera_system
from app.config import ROOT_DIR, settings
from app.vision.movement_analyzer import BodyMovementAnalyzer
from app.services.landmark_config import parse_groups

logger = logging.getLogger(__name__)

COCO_JOINT_NAMES = {
    0: "nose", 1: "left eye", 2: "right eye", 3: "left ear", 4: "right ear",
    5: "left shoulder", 6: "right shoulder", 7: "left elbow", 8: "right elbow",
    9: "left wrist", 10: "right wrist", 11: "left hip", 12: "right hip",
    13: "left knee", 14: "right knee", 15: "left ankle", 16: "right ankle",
}


def stable_missing_required_joints(
    confidence_samples: list[np.ndarray], required: set[int], threshold: float,
    minimum_samples: int = 3, required_ratio: float = 0.6,
) -> list[int]:
    """Reject sustained missing joints without failing on one noisy pose frame."""
    if not required or not confidence_samples:
        return sorted(required)
    samples = np.asarray(confidence_samples, dtype=float)
    if len(samples) < minimum_samples:
        return sorted(joint for joint in required if samples[-1, joint] < threshold)
    return sorted(
        joint for joint in required
        if float(np.mean(samples[:, joint] >= threshold)) < required_ratio
    )


@dataclass(slots=True)
class BodyState:
    tracking: bool = False
    status: str = "NO PERSON"
    device: str = "CPU"
    processing_fps: float = 0.0
    person_count: int = 0
    primary_subject_index: int | None = None
    movement_magnitude: float = 0.0
    regional_movement: dict[str, float] = field(default_factory=dict)
    movement_event: bool = False
    movement_events: int = 0
    movements_per_minute: float = 0.0
    posture_change: bool = False
    posture_changes: int = 0
    posture_angle: float | None = None
    body_scale: float = 0.0
    required_joints_visible: bool = False
    missing_required_joints: list[int] = field(default_factory=list)
    model_status: str = "NOT LOADED"
    inference_ms: float = 0.0


class BodyAnalysisService:
    def __init__(self) -> None:
        self.state = BodyState(device="CUDA" if torch.cuda.is_available() else "CPU")
        self._analyzer = BodyMovementAnalyzer(
            settings.body_movement_threshold, settings.body_movement_release,
            settings.body_movement_smoothing_alpha, settings.body_event_refractory_seconds,
            settings.posture_change_threshold_degrees,
        )
        self._model: YOLO | None = None
        self._annotated: np.ndarray | None = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_sequence = -1
        self._last_center: np.ndarray | None = None
        self._joint_confidence_history: deque[np.ndarray] = deque(
            maxlen=max(5, min(15, int(settings.body_process_fps)))
        )
        self._history_required: set[int] = set()
        self._missed_person_frames = 0

    def start(self) -> None:
        if settings.mock_mode or (self._thread and self._thread.is_alive()):
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="body-analysis", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            value = asdict(self.state)
        value["measured_groups"] = sorted(parse_groups(settings.body_measure_groups))
        value["missing_required_joint_names"] = [
            COCO_JOINT_NAMES.get(index, f"joint {index}") for index in value["missing_required_joints"]
        ]
        camera = camera_system.body.status_payload()
        age = camera.get("frame_age_seconds")
        if not settings.mock_mode and (camera["status"] != "CONNECTED" or age is None or age > 3):
            value.update(tracking=False, person_count=0, required_joints_visible=False,
                         status="CAMERA OFFLINE", processing_fps=0.0, regional_movement={},
                         movement_event=False, posture_change=False)
        return value

    def annotated_frame(self) -> np.ndarray | None:
        with self._lock:
            return None if self._annotated is None else self._annotated.copy()

    def _load_model(self) -> None:
        model_path = Path(settings.pose_model)
        if not model_path.is_absolute():
            model_path = ROOT_DIR / model_path
        self.state.model_status = "LOADING"
        self._model = YOLO(str(model_path))
        self.state.model_status = "READY"
        logger.info("YOLO Pose loaded on %s from %s", self.state.device, model_path)

    def _run(self) -> None:
        try:
            self._load_model()
        except Exception as exc:
            self.state.model_status = "LOAD FAILED"
            self.state.status = "MODEL ERROR"
            logger.exception("Unable to load body pose model: %s", exc)
            return
        frames = 0
        fps_started = time.monotonic()
        interval = 1 / max(settings.body_process_fps, 1)
        device = 0 if torch.cuda.is_available() else "cpu"
        while not self._stop.is_set():
            started = time.monotonic()
            frame, _, sequence = camera_system.body.latest_frame()
            if frame is None or sequence == self._last_sequence:
                self.state.status = "CAMERA OFFLINE" if camera_system.body.stats.status != "CONNECTED" else "NO PERSON"
                self._stop.wait(min(interval, 0.08))
                continue
            self._last_sequence = sequence
            assert self._model is not None
            inference_started = time.perf_counter()
            results = self._model.predict(
                frame, conf=settings.pose_confidence, device=device, verbose=False, max_det=5,
                imgsz=640,
            )
            self.state.inference_ms = round((time.perf_counter() - inference_started) * 1000, 1)
            result = results[0]
            count = 0 if result.keypoints is None else len(result.keypoints)
            self.state.person_count = count
            if count == 0:
                self._missed_person_frames += 1
                if self._missed_person_frames >= 3:
                    self._joint_confidence_history.clear()
                self.state.tracking = False
                self.state.required_joints_visible = False
                self.state.missing_required_joints = []
                self.state.status = "NO PERSON"
                annotated = frame
            else:
                self._missed_person_frames = 0
                index = self._select_primary(result)
                xy = result.keypoints.xy[index].cpu().numpy()
                confidence = result.keypoints.conf[index].cpu().numpy() if result.keypoints.conf is not None else np.ones(17)
                keypoints = np.column_stack((xy, confidence))
                update = self._analyzer.update(keypoints, time.monotonic(), settings.keypoint_confidence)
                self.state.tracking = True
                self.state.status = "TRACKING"
                self.state.primary_subject_index = index
                self.state.movement_magnitude = update.magnitude
                measured_groups = parse_groups(settings.body_measure_groups)
                group_joints = {"head_shoulders": [0, 5, 6], "torso": [5, 6, 11, 12],
                                "left_arm": [5, 7, 9], "right_arm": [6, 8, 10],
                                "left_leg": [11, 13, 15], "right_leg": [12, 14, 16]}
                required = {joint for group in measured_groups for joint in group_joints.get(group, [])}
                if required != self._history_required:
                    self._joint_confidence_history.clear()
                    self._history_required = set(required)
                self._joint_confidence_history.append(confidence.copy())
                self.state.missing_required_joints = stable_missing_required_joints(
                    list(self._joint_confidence_history), required, settings.keypoint_confidence
                )
                self.state.required_joints_visible = bool(required) and not self.state.missing_required_joints
                self.state.regional_movement = {key: value for key, value in update.regional.items()
                                                if key in measured_groups}
                self.state.movement_event = update.movement_event
                self.state.movement_events = update.total_events
                self.state.movements_per_minute = update.movements_per_minute
                self.state.posture_change = update.posture_change
                self.state.posture_changes = update.posture_changes
                self.state.posture_angle = update.posture_angle
                self.state.body_scale = update.body_scale
                annotated = self._draw_selected_groups(frame, keypoints, parse_groups(settings.body_display_groups)) \
                    if settings.show_body_skeleton else frame
            frames += 1
            elapsed = time.monotonic() - fps_started
            if elapsed >= 1:
                self.state.processing_fps = round(frames / elapsed, 1)
                frames = 0
                fps_started = time.monotonic()
            with self._lock:
                self._annotated = annotated
            self._stop.wait(max(0.0, interval - (time.monotonic() - started)))

    def _select_primary(self, result) -> int:
        boxes = result.boxes.xyxy.cpu().numpy()
        centers = np.column_stack(((boxes[:, 0] + boxes[:, 2]) / 2, (boxes[:, 1] + boxes[:, 3]) / 2))
        areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
        if self._last_center is None:
            index = int(np.argmax(areas))
        else:
            distances = np.linalg.norm(centers - self._last_center, axis=1)
            normalized = distances / np.maximum(np.sqrt(areas), 1)
            index = int(np.argmin(normalized))
        self._last_center = centers[index]
        return index

    @staticmethod
    def _draw_selected_groups(frame: np.ndarray, keypoints: np.ndarray, groups: set[str]) -> np.ndarray:
        annotated = frame.copy()
        group_paths = {
            "head_shoulders": [(0, 5), (0, 6), (5, 6)],
            "left_arm": [(5, 7), (7, 9)], "right_arm": [(6, 8), (8, 10)],
            "torso": [(5, 6), (5, 11), (6, 12), (11, 12)],
            "left_leg": [(11, 13), (13, 15)], "right_leg": [(12, 14), (14, 16)],
        }
        paths = [edge for group in groups for edge in group_paths.get(group, [])]
        indexes = {index for edge in paths for index in edge}
        for start, end in paths:
            if keypoints[start, 2] >= settings.keypoint_confidence and keypoints[end, 2] >= settings.keypoint_confidence:
                a = tuple(keypoints[start, :2].astype(int)); b = tuple(keypoints[end, :2].astype(int))
                cv2.line(annotated, a, b, (62, 196, 145), 2, cv2.LINE_AA)
        for index in indexes:
            if keypoints[index, 2] >= settings.keypoint_confidence:
                point = tuple(keypoints[index, :2].astype(int))
                cv2.circle(annotated, point, 4, (82, 171, 218), -1, cv2.LINE_AA)
        return annotated


body_analysis_service = BodyAnalysisService()
