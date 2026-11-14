"""Non-blocking facial landmark and blink-analysis worker."""

from __future__ import annotations

import logging
import hashlib
import json
import statistics
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

import cv2
import numpy as np

from app.camera.camera_system import camera_system
from app.config import settings
from app.database.repository import repository
from app.vision.blink_detector import BlinkDetector, eye_aspect_ratio
from app.vision.face_landmarks import (
    FACE_CONTOUR_CONNECTIONS, IRIS_CONNECTIONS, LEFT_EYE_INDICES,
    MOUTH_CONNECTIONS, RIGHT_EYE_INDICES, FaceLandmarkDetector,
)
from app.vision.head_pose import HeadMovementTracker, HeadPose, estimate_head_pose, neutral_angle
from app.vision.face_distance import distance_quality, estimate_face_distance_cm
from app.services.landmark_config import parse_groups

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FaceState:
    tracking: bool = False
    status: str = "NO FACE"
    left_ear: float | None = None
    right_ear: float | None = None
    average_ear: float | None = None
    eye_closed: bool = False
    total_blinks: int = 0
    blink_rate: float = 0.0
    processing_fps: float = 0.0
    threshold: float = settings.ear_threshold
    calibrated: bool = False
    calibration_status: str = "NOT CALIBRATED"
    yaw: float | None = None
    pitch: float | None = None
    roll: float | None = None
    head_direction: str = "UNKNOWN"
    horizontal_direction: str = "UNKNOWN"
    vertical_direction: str = "UNKNOWN"
    head_tilt: str = "UNKNOWN"
    head_movement_magnitude: float = 0.0
    head_movement_event: bool = False
    head_movements: int = 0
    head_movements_per_minute: float = 0.0
    head_calibrated: bool = False
    head_calibration_status: str = "NOT CALIBRATED"
    inference_ms: float = 0.0
    estimated_distance_cm: float | None = None
    distance_quality: str = "red"
    distance_instruction: str = "Distance unavailable — keep both eyes visible"
    last_blink_minimum_ear: float | None = None
    last_blink_duration_seconds: float | None = None
    rejected_long_closures: int = 0


class FaceAnalysisService:
    def __init__(self) -> None:
        self.state = FaceState()
        self._detector: FaceLandmarkDetector | None = None
        self._blink = BlinkDetector(
            settings.ear_threshold,
            settings.min_closed_frames,
            settings.blink_refractory_seconds,
            settings.blink_rate_window_seconds,
            settings.max_closed_seconds,
        )
        self._head = HeadMovementTracker(
            settings.head_pose_smoothing_alpha,
            settings.head_movement_threshold_degrees,
            settings.head_movement_release_degrees,
            settings.head_movement_refractory_seconds,
            settings.head_rate_window_seconds,
        )
        self._annotated: np.ndarray | None = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_sequence = -1
        self._calibration_until = 0.0
        self._calibration_samples: list[float] = []
        self._head_calibration_until = 0.0
        self._head_calibration_samples: list[HeadPose] = []

    @staticmethod
    def _calibration_key() -> str:
        """Fingerprint inputs that make a saved face/head baseline reusable."""
        value = {
            "source": settings.face_camera_source,
            "format": [settings.face_camera_width, settings.face_camera_height, settings.face_camera_fps],
            "ear": [settings.ear_threshold, settings.min_closed_frames],
            "head": [settings.head_pose_smoothing_alpha, settings.head_movement_threshold_degrees,
                     settings.head_movement_release_degrees],
        }
        canonical = json.dumps(value, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _update_saved_calibration(self, **changes: object) -> None:
        """Persist completed baselines in the installation setup record."""
        item = repository.get_system_setup_state()
        if item is None:
            return
        try:
            progress = json.loads(item.progress_json or "{}")
        except (TypeError, json.JSONDecodeError):
            progress = {}
        if not isinstance(progress, dict):
            progress = {}
        step = dict(progress.get("step_5") or {})
        step.update(changes)
        step["calibration_key"] = self._calibration_key()
        step["calibration_saved_at"] = datetime.now(timezone.utc).isoformat()
        progress["step_5"] = step
        progress["last_saved_at"] = datetime.now(timezone.utc).isoformat()
        repository.save_system_setup_state(
            status="in_progress", current_step=5,
            progress_json=json.dumps(progress, sort_keys=True),
        )

    def _clear_saved_calibration(self, kind: str) -> None:
        changes: dict[str, object] = {"ready": False}
        if kind == "eye":
            changes.update(eye_baseline=None, eye_threshold=None, eye_calibrated_at=None)
        else:
            changes.update(neutral_head=None, head_calibrated_at=None)
        self._update_saved_calibration(**changes)

    def restore_saved_calibration(self) -> bool:
        """Restore database-backed baselines after an application restart."""
        item = repository.get_system_setup_state()
        if item is None:
            return False
        try:
            progress = json.loads(item.progress_json or "{}")
        except (TypeError, json.JSONDecodeError):
            return False
        step = progress.get("step_5") if isinstance(progress, dict) else None
        if not isinstance(step, dict) or step.get("calibration_key") != self._calibration_key():
            return False
        restored = False
        baseline = step.get("eye_baseline")
        threshold = step.get("eye_threshold")
        if isinstance(baseline, (int, float)) and baseline > 0 and isinstance(threshold, (int, float)) and threshold > 0:
            self._blink.threshold = float(threshold)
            self.state.threshold = round(float(threshold), 3)
            self.state.calibrated = True
            self.state.calibration_status = f"CALIBRATED (restored baseline EAR {float(baseline):.3f})"
            restored = True
        neutral = step.get("neutral_head")
        if isinstance(neutral, dict) and all(isinstance(neutral.get(key), (int, float)) for key in ("yaw", "pitch", "roll")):
            self._head.set_neutral(float(neutral["yaw"]), float(neutral["pitch"]), float(neutral["roll"]))
            self.state.head_calibrated = True
            self.state.head_calibration_status = "CALIBRATED (restored relative baseline)"
            restored = True
        if restored:
            logger.info("Restored saved face/head calibration from the database")
        return restored

    def start(self) -> None:
        if settings.mock_mode or (self._thread and self._thread.is_alive()):
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="face-analysis", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        if self._detector:
            self._detector.close()
            self._detector = None

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            value = asdict(self.state)
        camera = camera_system.face.status_payload()
        age = camera.get("frame_age_seconds")
        if not settings.mock_mode and (camera["status"] != "CONNECTED" or age is None or age > 3):
            value.update(tracking=False, status="CAMERA OFFLINE", processing_fps=0.0,
                         head_movement_event=False, estimated_distance_cm=None,
                         yaw=None, pitch=None, roll=None, head_direction="UNKNOWN",
                         horizontal_direction="UNKNOWN", vertical_direction="UNKNOWN", head_tilt="UNKNOWN")
        return value

    def annotated_frame(self) -> np.ndarray | None:
        with self._lock:
            return None if self._annotated is None else self._annotated.copy()

    def start_calibration(self, duration_seconds: float = 10.0) -> None:
        self._clear_saved_calibration("eye")
        self.state.calibrated = False
        self._calibration_samples.clear()
        self._calibration_until = time.monotonic() + duration_seconds
        self.state.calibration_status = "CALIBRATING — look at the center and keep eyes normally open"

    def start_head_calibration(self, duration_seconds: float = 10.0) -> None:
        self._clear_saved_calibration("head")
        self.state.head_calibrated = False
        self._head_calibration_samples.clear()
        self._head_calibration_until = time.monotonic() + duration_seconds
        self.state.head_calibration_status = "CALIBRATING — sit normally and look at the center"

    def _run(self) -> None:
        self._detector = FaceLandmarkDetector()
        frames = 0
        fps_started = time.monotonic()
        interval = 1 / max(settings.face_process_fps, 1)
        while not self._stop.is_set():
            loop_started = time.monotonic()
            frame, _, sequence = camera_system.face.latest_frame()
            if frame is None or sequence == self._last_sequence:
                self._stop.wait(min(interval, 0.05))
                continue
            self._last_sequence = sequence
            inference_started = time.perf_counter()
            result = self._detector.process(frame)
            self.state.inference_ms = round((time.perf_counter() - inference_started) * 1000, 1)
            now = time.monotonic()
            annotated = frame.copy()
            if result is None:
                self.state.tracking = False
                self.state.status = "NO FACE"
                self._clear_head_tracking()
            else:
                left = eye_aspect_ratio(result.left_eye)
                right = eye_aspect_ratio(result.right_eye)
                average = (left + right) / 2
                update = self._blink.update(average, now)
                self.state.tracking = True
                self.state.status = "TRACKING"
                self.state.left_ear = round(left, 3)
                self.state.right_ear = round(right, 3)
                self.state.average_ear = round(average, 3)
                self.state.eye_closed = update.eye_closed
                self.state.total_blinks = update.total_blinks
                self.state.blink_rate = update.blinks_per_minute
                if update.blink:
                    self.state.last_blink_minimum_ear = update.minimum_ear
                    self.state.last_blink_duration_seconds = update.closure_duration_seconds
                if update.rejected_long_closure and not update.eye_closed:
                    self.state.rejected_long_closures += 1
                self.state.threshold = round(self._blink.threshold, 3)
                distance = estimate_face_distance_cm(result.left_eye, result.right_eye, frame.shape[1], frame.shape[0])
                if distance is not None:
                    previous = self.state.estimated_distance_cm
                    distance = distance if previous is None else round(0.25 * distance + 0.75 * previous, 1)
                quality, instruction = distance_quality(distance)
                self.state.estimated_distance_cm = distance
                self.state.distance_quality = quality
                self.state.distance_instruction = instruction
                self._handle_calibration(average, now)
                height, width = annotated.shape[:2]
                raw_pose = estimate_head_pose(result.normalized, width, height)
                if raw_pose is not None:
                    self._handle_head_calibration(raw_pose, now)
                    if self.state.head_calibrated:
                        head = self._head.update(raw_pose, now)
                        self.state.yaw = head.pose.yaw
                        self.state.pitch = head.pose.pitch
                        self.state.roll = head.pose.roll
                        self.state.head_direction = head.direction
                        self.state.horizontal_direction = head.horizontal
                        self.state.vertical_direction = head.vertical
                        self.state.head_tilt = head.tilt
                        self.state.head_movement_magnitude = head.magnitude
                        self.state.head_movement_event = head.movement_event
                        self.state.head_movements = head.total_movements
                        self.state.head_movements_per_minute = head.movements_per_minute
                    else:
                        self._clear_head_tracking()
                        self.state.head_direction = "CALIBRATE"
                else:
                    self._clear_head_tracking()
                if settings.show_face_landmarks:
                    display_groups = parse_groups(settings.face_display_groups)
                    if "eyes" in display_groups:
                        self._draw_points(annotated, result.normalized,
                                          (*LEFT_EYE_INDICES, *RIGHT_EYE_INDICES), (70, 240, 160))
                    if "iris" in display_groups:
                        self._draw_connections(annotated, result.normalized,
                                               IRIS_CONNECTIONS, (255, 210, 70), 1)
                    if "mouth" in display_groups:
                        self._draw_connections(annotated, result.normalized,
                                               MOUTH_CONNECTIONS, (210, 120, 255), 1)
                    if "face_contour" in display_groups:
                        self._draw_connections(annotated, result.normalized,
                                               FACE_CONTOUR_CONNECTIONS, (90, 200, 255), 1)
                label = f"EAR {average:.3f} | Blinks {update.total_blinks} | {update.blinks_per_minute:.1f}/min"
                cv2.putText(annotated, label, (16, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (70, 240, 160), 2)
                pose_label = f"H: {self.state.horizontal_direction} | V: {self.state.vertical_direction}"
                cv2.putText(annotated, pose_label, (16, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (90, 200, 255), 2)
            frames += 1
            elapsed = now - fps_started
            if elapsed >= 1:
                self.state.processing_fps = round(frames / elapsed, 1)
                frames = 0
                fps_started = now
            with self._lock:
                self._annotated = annotated
            self._stop.wait(max(0.0, interval - (time.monotonic() - loop_started)))

    def _clear_head_tracking(self) -> None:
        self._head.reset_tracking()
        self.state.yaw = self.state.pitch = self.state.roll = None
        self.state.head_direction = "UNKNOWN"
        self.state.horizontal_direction = self.state.vertical_direction = self.state.head_tilt = "UNKNOWN"
        self.state.head_movement_event = False
        self.state.head_movement_magnitude = 0.0

    @staticmethod
    def _draw_points(frame: np.ndarray, points: tuple[tuple[float, float, float], ...],
                     indices: tuple[int, ...], color: tuple[int, int, int]) -> None:
        height, width = frame.shape[:2]
        for index in indices:
            x, y, _ = points[index]
            cv2.circle(frame, (int(x * width), int(y * height)), 2, color, -1)

    @staticmethod
    def _draw_connections(frame: np.ndarray, points: tuple[tuple[float, float, float], ...],
                          connections: tuple[tuple[int, int], ...],
                          color: tuple[int, int, int], thickness: int) -> None:
        height, width = frame.shape[:2]
        for start, end in connections:
            x1, y1, _ = points[start]
            x2, y2, _ = points[end]
            cv2.line(frame, (int(x1 * width), int(y1 * height)),
                     (int(x2 * width), int(y2 * height)), color, thickness, cv2.LINE_AA)

    def _handle_calibration(self, average_ear: float, now: float) -> None:
        if not self._calibration_until:
            return
        if now <= self._calibration_until:
            self._calibration_samples.append(average_ear)
            return
        self._calibration_until = 0.0
        if len(self._calibration_samples) >= 10:
            baseline = statistics.median(self._calibration_samples)
            threshold = self._blink.set_calibrated_threshold(baseline)
            self.state.threshold = round(threshold, 3)
            self.state.calibrated = True
            self.state.calibration_status = f"CALIBRATED (baseline EAR {baseline:.3f})"
            self._update_saved_calibration(
                eye_baseline=round(float(baseline), 6),
                eye_threshold=round(float(threshold), 6),
                eye_calibrated_at=datetime.now(timezone.utc).isoformat(),
            )
            logger.info("Face calibration complete: baseline EAR %.3f, threshold %.3f", baseline, threshold)
        else:
            self.state.calibration_status = "CALIBRATION FAILED — insufficient face samples"

    def _handle_head_calibration(self, raw_pose: HeadPose, now: float) -> None:
        if not self._head_calibration_until:
            return
        if now <= self._head_calibration_until:
            self._head_calibration_samples.append(raw_pose)
            return
        self._head_calibration_until = 0.0
        if len(self._head_calibration_samples) >= 10:
            yaw = neutral_angle([item.yaw for item in self._head_calibration_samples])
            pitch = neutral_angle([item.pitch for item in self._head_calibration_samples])
            roll = neutral_angle([item.roll for item in self._head_calibration_samples])
            spreads = [statistics.median(abs(self._head._angular_delta(getattr(item, axis), center))
                       for item in self._head_calibration_samples)
                       for axis, center in [("yaw", yaw), ("pitch", pitch), ("roll", roll)]]
            if max(spreads) > 8:
                self.state.head_calibration_status = "CALIBRATION FAILED — hold your head still and retry"
                return
            self._head.set_neutral(yaw, pitch, roll)
            self.state.head_calibrated = True
            # Raw solvePnP Euler angles can legitimately wrap near ±180°. Operators
            # should see the meaningful relative baseline, not confusing camera-space values.
            self.state.head_calibration_status = "CALIBRATED (relative angles reset to 0°)"
            self._update_saved_calibration(
                neutral_head={"yaw": float(yaw), "pitch": float(pitch), "roll": float(roll)},
                head_calibrated_at=datetime.now(timezone.utc).isoformat(),
            )
            logger.info("Head calibration complete: yaw %.1f, pitch %.1f, roll %.1f", yaw, pitch, roll)
        else:
            self.state.head_calibration_status = "CALIBRATION FAILED — insufficient pose samples"


face_analysis_service = FaceAnalysisService()
