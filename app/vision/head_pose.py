"""Head-pose estimation, smoothing, calibration, and movement events."""

from __future__ import annotations

import math
import statistics
from collections import deque
from dataclasses import dataclass
from typing import Sequence

import cv2
import numpy as np

# MediaPipe Face Mesh landmarks corresponding to stable facial anchors.
POSE_LANDMARK_INDICES = (1, 152, 33, 263, 61, 291)

# Generic 3D face model in millimeters. It is used for orientation, not identity.
MODEL_POINTS = np.array(
    [
        (0.0, 0.0, 0.0),
        (0.0, -63.6, -12.5),
        (-43.3, 32.7, -26.0),
        (43.3, 32.7, -26.0),
        (-28.9, -28.9, -24.1),
        (28.9, -28.9, -24.1),
    ],
    dtype=np.float64,
)


@dataclass(frozen=True, slots=True)
class HeadPose:
    yaw: float
    pitch: float
    roll: float


@dataclass(frozen=True, slots=True)
class HeadMovementUpdate:
    pose: HeadPose
    direction: str
    magnitude: float
    movement_event: bool
    total_movements: int
    movements_per_minute: float
    horizontal: str = "CENTER"
    vertical: str = "CENTER"
    tilt: str = "LEVEL"


def neutral_angle(values: Sequence[float]) -> float:
    """Median around a circular anchor; +179 and -179 must not average to zero."""
    anchor = math.degrees(math.atan2(sum(math.sin(math.radians(v)) for v in values),
                                    sum(math.cos(math.radians(v)) for v in values)))
    return (anchor + statistics.median((v - anchor + 180) % 360 - 180 for v in values) + 180) % 360 - 180


def estimate_head_pose(
    normalized_landmarks: Sequence[tuple[float, float, float]], width: int, height: int
) -> HeadPose | None:
    """Estimate camera-relative Euler angles with OpenCV solvePnP."""
    if len(normalized_landmarks) <= max(POSE_LANDMARK_INDICES) or width <= 0 or height <= 0:
        return None
    image_points = np.array(
        [(normalized_landmarks[index][0] * width, normalized_landmarks[index][1] * height) for index in POSE_LANDMARK_INDICES],
        dtype=np.float64,
    )
    if not np.isfinite(image_points).all():
        return None
    focal_length = float(width)
    camera_matrix = np.array(
        [[focal_length, 0, width / 2], [0, focal_length, height / 2], [0, 0, 1]], dtype=np.float64
    )
    distortion = np.zeros((4, 1), dtype=np.float64)
    if np.ptp(image_points[:, 0]) < 1 or np.ptp(image_points[:, 1]) < 1:
        return None
    try:
        success, rotation_vector, translation = cv2.solvePnP(
            MODEL_POINTS, image_points, camera_matrix, distortion, flags=cv2.SOLVEPNP_ITERATIVE
        )
    except cv2.error:
        return None
    if not success:
        return None
    projected, _ = cv2.projectPoints(MODEL_POINTS, rotation_vector, translation, camera_matrix, distortion)
    error = np.sqrt(np.mean(np.sum((projected.reshape(-1, 2) - image_points) ** 2, axis=1)))
    if not math.isfinite(error) or error > width * .04:
        return None
    rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
    angles, *_ = cv2.RQDecomp3x3(rotation_matrix)
    pitch, yaw, roll = (float(value) for value in angles)
    return HeadPose(yaw=yaw, pitch=pitch, roll=roll)


class HeadMovementTracker:
    """Apply EMA smoothing and count threshold crossings with hysteresis."""

    def __init__(
        self,
        smoothing_alpha: float,
        threshold_degrees: float,
        release_degrees: float,
        refractory_seconds: float,
        rate_window_seconds: float = 60.0,
        direction_hold_seconds: float = .25,
    ) -> None:
        if not 0 < smoothing_alpha <= 1:
            raise ValueError("smoothing_alpha must be in (0, 1]")
        if release_degrees >= threshold_degrees:
            raise ValueError("release threshold must be below movement threshold")
        self.alpha = smoothing_alpha
        self.threshold = threshold_degrees
        self.release = release_degrees
        self.refractory = refractory_seconds
        self.rate_window = rate_window_seconds
        self.neutral = HeadPose(0.0, 0.0, 0.0)
        self.smoothed: HeadPose | None = None
        self.active = False
        self.last_event_at = float("-inf")
        self.total_movements = 0
        self.timestamps: deque[float] = deque()
        self.direction_hold = direction_hold_seconds
        self.axes = ["CENTER", "CENTER", "LEVEL"]
        self.candidates = list(self.axes)
        self.candidate_since = [0.0] * 3

    def reset_tracking(self) -> None:
        self.smoothed = None
        self.active = False
        self.axes = ["CENTER", "CENTER", "LEVEL"]
        self.candidates = list(self.axes)
        self.candidate_since = [0.0] * 3

    def set_neutral(self, yaw: float, pitch: float, roll: float) -> None:
        self.neutral = HeadPose(yaw, pitch, roll)
        self.reset_tracking()

    def update(self, raw: HeadPose, timestamp: float) -> HeadMovementUpdate:
        relative = HeadPose(
            self._angular_delta(raw.yaw, self.neutral.yaw),
            self._angular_delta(raw.pitch, self.neutral.pitch),
            self._angular_delta(raw.roll, self.neutral.roll),
        )
        if self.smoothed is None:
            self.smoothed = relative
        else:
            a = self.alpha
            self.smoothed = HeadPose(
                self.smoothed.yaw + a * self._angular_delta(relative.yaw, self.smoothed.yaw),
                self.smoothed.pitch + a * self._angular_delta(relative.pitch, self.smoothed.pitch),
                self.smoothed.roll + a * self._angular_delta(relative.roll, self.smoothed.roll),
            )
        pose = self.smoothed
        magnitude = math.sqrt(pose.yaw**2 + pose.pitch**2 + pose.roll**2)
        event = False
        if not self.active and magnitude >= self.threshold and timestamp - self.last_event_at >= self.refractory:
            event = True
            self.active = True
            self.last_event_at = timestamp
            self.total_movements += 1
            self.timestamps.append(timestamp)
        elif self.active and magnitude <= self.release:
            self.active = False
        cutoff = timestamp - self.rate_window
        while self.timestamps and self.timestamps[0] < cutoff:
            self.timestamps.popleft()
        observed_window = min(max(timestamp, 1.0), self.rate_window)
        rate = len(self.timestamps) * 60.0 / observed_window
        for index, (value, negative, positive, center) in enumerate([
                (pose.yaw, "LEFT", "RIGHT", "CENTER"),
                (pose.pitch, "UP", "DOWN", "CENTER"),
                (pose.roll, "TILT LEFT", "TILT RIGHT", "LEVEL")]):
            boundary = self.release if self.axes[index] != center else max(self.release + 2, self.threshold * .75)
            candidate = center if abs(value) < boundary else positive if value > 0 else negative
            if candidate != self.candidates[index]:
                self.candidates[index] = candidate
                self.candidate_since[index] = timestamp
            if timestamp - self.candidate_since[index] >= self.direction_hold:
                self.axes[index] = candidate
        direction = self.axes[0] if abs(pose.yaw) >= abs(pose.pitch) else self.axes[1]
        if direction == "CENTER":
            direction = self.axes[1] if self.axes[0] == "CENTER" else self.axes[0]
        if self.axes[0] == self.axes[1] == "CENTER":
            direction = "CENTER"
        return HeadMovementUpdate(
            HeadPose(round(pose.yaw, 1), round(pose.pitch, 1), round(pose.roll, 1)),
            direction,
            round(magnitude, 1),
            event,
            self.total_movements,
            round(rate, 1),
            *self.axes,
        )

    @staticmethod
    def _angular_delta(value: float, neutral: float) -> float:
        """Return the shortest signed difference, avoiding ±180° jumps."""
        return (value - neutral + 180.0) % 360.0 - 180.0
