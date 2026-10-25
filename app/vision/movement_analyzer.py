"""Body-scale-normalized regional movement and posture-change measurements."""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field

import numpy as np

REGIONS = {
    "head_shoulders": (0, 5, 6),
    "left_arm": (5, 7, 9),
    "right_arm": (6, 8, 10),
    "torso": (5, 6, 11, 12),
    "left_leg": (11, 13, 15),
    "right_leg": (12, 14, 16),
}


@dataclass(frozen=True, slots=True)
class BodyMovementUpdate:
    magnitude: float
    regional: dict[str, float]
    movement_event: bool
    total_events: int
    movements_per_minute: float
    posture_change: bool
    posture_changes: int
    posture_angle: float | None
    body_scale: float


class BodyMovementAnalyzer:
    """Compare COCO keypoints frame-to-frame after normalizing by body scale."""

    def __init__(self, threshold: float, release: float, alpha: float, refractory: float, posture_threshold: float) -> None:
        self.threshold = threshold
        self.release = release
        self.alpha = alpha
        self.refractory = refractory
        self.posture_threshold = posture_threshold
        self.previous: np.ndarray | None = None
        self.smoothed = 0.0
        self.active = False
        self.last_event_at = float("-inf")
        self.event_times: deque[float] = deque()
        self.total_events = 0
        self.last_posture_angle: float | None = None
        self.last_posture_at = float("-inf")
        self.posture_changes = 0

    def update(self, keypoints: np.ndarray, timestamp: float, confidence_threshold: float) -> BodyMovementUpdate:
        if keypoints.shape != (17, 3):
            raise ValueError("Expected COCO keypoints with shape (17, 3)")
        scale = self._body_scale(keypoints, confidence_threshold)
        regional = {name: 0.0 for name in REGIONS}
        raw = 0.0
        if self.previous is not None and scale > 1e-6:
            values = []
            for name, indices in REGIONS.items():
                distances = []
                for index in indices:
                    if keypoints[index, 2] >= confidence_threshold and self.previous[index, 2] >= confidence_threshold:
                        distances.append(float(np.linalg.norm(keypoints[index, :2] - self.previous[index, :2]) / scale))
                regional[name] = round(float(np.mean(distances)) if distances else 0.0, 4)
                values.extend(distances)
            raw = float(np.mean(values)) if values else 0.0
        self.smoothed = self.alpha * raw + (1 - self.alpha) * self.smoothed
        event = False
        if not self.active and self.smoothed >= self.threshold and timestamp - self.last_event_at >= self.refractory:
            self.active = True
            event = True
            self.last_event_at = timestamp
            self.total_events += 1
            self.event_times.append(timestamp)
        elif self.active and self.smoothed <= self.release:
            self.active = False
        posture_angle = self._torso_angle(keypoints, confidence_threshold)
        posture_change = False
        if posture_angle is not None:
            if (
                self.last_posture_angle is not None
                and abs(posture_angle - self.last_posture_angle) >= self.posture_threshold
                and timestamp - self.last_posture_at >= self.refractory
            ):
                posture_change = True
                self.posture_changes += 1
                self.last_posture_at = timestamp
            self.last_posture_angle = posture_angle
        self.previous = keypoints.copy()
        cutoff = timestamp - 60
        while self.event_times and self.event_times[0] < cutoff:
            self.event_times.popleft()
        observed = min(max(timestamp, 1.0), 60.0)
        return BodyMovementUpdate(
            round(self.smoothed, 4), regional, event, self.total_events,
            round(len(self.event_times) * 60 / observed, 1), posture_change,
            self.posture_changes, None if posture_angle is None else round(posture_angle, 1), round(scale, 2),
        )

    @staticmethod
    def _body_scale(keypoints: np.ndarray, threshold: float) -> float:
        visible = keypoints[:, 2] >= threshold
        if visible.sum() < 2:
            return 0.0
        points = keypoints[visible, :2]
        diagonal = float(np.linalg.norm(points.max(axis=0) - points.min(axis=0)))
        return max(diagonal, 1e-6)

    @staticmethod
    def _torso_angle(keypoints: np.ndarray, threshold: float) -> float | None:
        required = (5, 6, 11, 12)
        if any(keypoints[index, 2] < threshold for index in required):
            return None
        shoulders = (keypoints[5, :2] + keypoints[6, :2]) / 2
        hips = (keypoints[11, :2] + keypoints[12, :2]) / 2
        vector = shoulders - hips
        return math.degrees(math.atan2(float(vector[0]), float(-vector[1])))

