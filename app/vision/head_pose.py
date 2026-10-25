"""Head-pose estimation, smoothing, calibration, and movement events."""

from __future__ import annotations

import math
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
    focal_length = float(width)
    camera_matrix = np.array(
        [[focal_length, 0, width / 2], [0, focal_length, height / 2], [0, 0, 1]], dtype=np.float64
    )
    distortion = np.zeros((4, 1), dtype=np.float64)
    success, rotation_vector, _ = cv2.solvePnP(
        MODEL_POINTS, image_points, camera_matrix, distortion, flags=cv2.SOLVEPNP_ITERATIVE
    )
    if not success:
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

    def set_neutral(self, yaw: float, pitch: float, roll: float) -> None:
        self.neutral = HeadPose(yaw, pitch, roll)
        self.smoothed = None
        self.active = False

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
                a * relative.yaw + (1 - a) * self.smoothed.yaw,
                a * relative.pitch + (1 - a) * self.smoothed.pitch,
                a * relative.roll + (1 - a) * self.smoothed.roll,
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
        return HeadMovementUpdate(
            HeadPose(round(pose.yaw, 1), round(pose.pitch, 1), round(pose.roll, 1)),
            self._direction(pose),
            round(magnitude, 1),
            event,
            self.total_movements,
            round(rate, 1),
        )

    def _direction(self, pose: HeadPose) -> str:
        horizontal = abs(pose.yaw)
        vertical = abs(pose.pitch)
        if max(horizontal, vertical) < self.release:
            return "CENTER"
        if horizontal >= vertical:
            return "RIGHT" if pose.yaw > 0 else "LEFT"
        # Verified against the deployed camera: calibrated negative pitch is
        # an upward head tilt and positive pitch is a downward head tilt.
        return "DOWN" if pose.pitch > 0 else "UP"

    @staticmethod
    def _angular_delta(value: float, neutral: float) -> float:
        """Return the shortest signed difference, avoiding ±180° jumps."""
        return (value - neutral + 180.0) % 360.0 - 180.0
