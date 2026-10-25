"""MediaPipe Face Mesh adapter exposing normalized structured landmarks."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import mediapipe as mp
import numpy as np

LEFT_EYE_INDICES = (33, 160, 158, 133, 153, 144)
RIGHT_EYE_INDICES = (362, 385, 387, 263, 373, 380)
NOSE_INDEX = 1
IRIS_CONNECTIONS = tuple(mp.solutions.face_mesh.FACEMESH_IRISES)
MOUTH_CONNECTIONS = tuple(mp.solutions.face_mesh.FACEMESH_LIPS)
FACE_CONTOUR_CONNECTIONS = tuple(mp.solutions.face_mesh.FACEMESH_FACE_OVAL)


@dataclass(frozen=True, slots=True)
class FaceLandmarkResult:
    normalized: tuple[tuple[float, float, float], ...]
    left_eye: tuple[tuple[float, float], ...]
    right_eye: tuple[tuple[float, float], ...]
    nose: tuple[float, float, float]


class FaceLandmarkDetector:
    def __init__(self) -> None:
        self._mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def process(self, frame_bgr: np.ndarray) -> FaceLandmarkResult | None:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        result = self._mesh.process(rgb)
        if not result.multi_face_landmarks:
            return None
        points = tuple((item.x, item.y, item.z) for item in result.multi_face_landmarks[0].landmark)
        left = tuple((points[index][0], points[index][1]) for index in LEFT_EYE_INDICES)
        right = tuple((points[index][0], points[index][1]) for index in RIGHT_EYE_INDICES)
        return FaceLandmarkResult(points, left, right, points[NOSE_INDEX])

    def close(self) -> None:
        self._mesh.close()
