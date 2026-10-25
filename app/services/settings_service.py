"""Safe, allow-listed persistence of operator-editable settings."""

from __future__ import annotations

import shutil
from pathlib import Path

from dotenv import set_key

from app.config import ROOT_DIR, settings

ENV_PATH = ROOT_DIR / ".env"
BACKUP_PATH = ROOT_DIR / ".env.backup"

FIELD_TO_ENV = {
    "face_camera_source": "FACE_CAMERA_SOURCE", "body_camera_source": "BODY_CAMERA_SOURCE",
    "camera_width": "CAMERA_WIDTH",
    "camera_height": "CAMERA_HEIGHT", "camera_fps": "CAMERA_FPS",
    "face_camera_width": "FACE_CAMERA_WIDTH", "face_camera_height": "FACE_CAMERA_HEIGHT",
    "face_camera_fps": "FACE_CAMERA_FPS", "body_camera_width": "BODY_CAMERA_WIDTH",
    "body_camera_height": "BODY_CAMERA_HEIGHT", "body_camera_fps": "BODY_CAMERA_FPS",
    "face_process_fps": "FACE_PROCESS_FPS", "body_process_fps": "BODY_PROCESS_FPS",
    "ear_threshold": "EAR_THRESHOLD", "min_closed_frames": "MIN_CLOSED_FRAMES",
    "blink_refractory_seconds": "BLINK_REFRACTORY_SECONDS",
    "head_pose_smoothing_alpha": "HEAD_POSE_SMOOTHING_ALPHA",
    "head_movement_threshold_degrees": "HEAD_MOVEMENT_THRESHOLD_DEGREES",
    "body_movement_threshold": "BODY_MOVEMENT_THRESHOLD",
    "posture_change_threshold_degrees": "POSTURE_CHANGE_THRESHOLD_DEGREES",
    "pose_confidence": "POSE_CONFIDENCE", "keypoint_confidence": "KEYPOINT_CONFIDENCE",
    "show_face_landmarks": "SHOW_FACE_LANDMARKS", "show_body_skeleton": "SHOW_BODY_SKELETON",
    "landmark_profile": "LANDMARK_PROFILE", "face_display_groups": "FACE_DISPLAY_GROUPS",
    "face_measure_groups": "FACE_MEASURE_GROUPS", "body_display_groups": "BODY_DISPLAY_GROUPS",
    "body_measure_groups": "BODY_MEASURE_GROUPS", "feature_types": "FEATURE_TYPES",
    "save_raw_video": "SAVE_RAW_VIDEO",
}


def current_settings() -> dict[str, object]:
    return {field: getattr(settings, field) for field in FIELD_TO_ENV}


def save_settings(values: dict[str, object]) -> None:
    if ENV_PATH.exists():
        shutil.copy2(ENV_PATH, BACKUP_PATH)
    for field, value in values.items():
        env_name = FIELD_TO_ENV[field]
        serialized = str(value).lower() if isinstance(value, bool) else str(value)
        set_key(str(ENV_PATH), env_name, serialized, quote_mode="never")
