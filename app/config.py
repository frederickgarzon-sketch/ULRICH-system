"""Central application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


def _bool_env(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Behavior Monitor Research Console")
    # A fresh installation must never silently generate synthetic participant data.
    app_mode: str = os.getenv("APP_MODE", "real").lower()
    server_host: str = os.getenv("SERVER_HOST", "0.0.0.0")
    server_port: int = int(os.getenv("SERVER_PORT", "8000"))
    database_url: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{(ROOT_DIR / 'data' / 'behavioral_monitoring.db').as_posix()}"
    )
    face_camera_source: str = os.getenv("FACE_CAMERA_SOURCE", "http://adhd-camera.local:8090/stream/face")
    body_camera_source: str = os.getenv("BODY_CAMERA_SOURCE", "http://adhd-camera.local:8090/stream/body")
    camera_width: int = int(os.getenv("CAMERA_WIDTH", "1280"))
    camera_height: int = int(os.getenv("CAMERA_HEIGHT", "720"))
    camera_fps: int = int(os.getenv("CAMERA_FPS", "20"))
    face_camera_width: int = int(os.getenv("FACE_CAMERA_WIDTH", os.getenv("CAMERA_WIDTH", "1280")))
    face_camera_height: int = int(os.getenv("FACE_CAMERA_HEIGHT", os.getenv("CAMERA_HEIGHT", "720")))
    face_camera_fps: int = int(os.getenv("FACE_CAMERA_FPS", os.getenv("CAMERA_FPS", "20")))
    body_camera_width: int = int(os.getenv("BODY_CAMERA_WIDTH", os.getenv("CAMERA_WIDTH", "1280")))
    body_camera_height: int = int(os.getenv("BODY_CAMERA_HEIGHT", os.getenv("CAMERA_HEIGHT", "720")))
    body_camera_fps: int = int(os.getenv("BODY_CAMERA_FPS", os.getenv("CAMERA_FPS", "20")))
    face_process_fps: int = int(os.getenv("FACE_PROCESS_FPS", "15"))
    body_process_fps: int = int(os.getenv("BODY_PROCESS_FPS", "10"))
    camera_reconnect_seconds: float = float(os.getenv("CAMERA_RECONNECT_SECONDS", "2.0"))
    camera_failure_limit: int = int(os.getenv("CAMERA_FAILURE_LIMIT", "10"))
    ear_threshold: float = float(os.getenv("EAR_THRESHOLD", "0.21"))
    min_closed_frames: int = int(os.getenv("MIN_CLOSED_FRAMES", "2"))
    max_closed_seconds: float = float(os.getenv("MAX_CLOSED_SECONDS", "1.5"))
    blink_refractory_seconds: float = float(os.getenv("BLINK_REFRACTORY_SECONDS", "0.15"))
    blink_rate_window_seconds: float = float(os.getenv("BLINK_RATE_WINDOW_SECONDS", "60"))
    show_face_landmarks: bool = _bool_env("SHOW_FACE_LANDMARKS", True)
    head_pose_smoothing_alpha: float = float(os.getenv("HEAD_POSE_SMOOTHING_ALPHA", "0.25"))
    head_movement_threshold_degrees: float = float(os.getenv("HEAD_MOVEMENT_THRESHOLD_DEGREES", "12"))
    head_movement_release_degrees: float = float(os.getenv("HEAD_MOVEMENT_RELEASE_DEGREES", "7"))
    head_movement_refractory_seconds: float = float(os.getenv("HEAD_MOVEMENT_REFRACTORY_SECONDS", "0.75"))
    head_rate_window_seconds: float = float(os.getenv("HEAD_RATE_WINDOW_SECONDS", "60"))
    pose_model: str = os.getenv("POSE_MODEL", "models/yolo11n-pose.pt")
    pose_confidence: float = float(os.getenv("POSE_CONFIDENCE", "0.45"))
    body_movement_threshold: float = float(os.getenv("BODY_MOVEMENT_THRESHOLD", "0.035"))
    body_movement_release: float = float(os.getenv("BODY_MOVEMENT_RELEASE", "0.018"))
    body_movement_smoothing_alpha: float = float(os.getenv("BODY_MOVEMENT_SMOOTHING_ALPHA", "0.3"))
    body_event_refractory_seconds: float = float(os.getenv("BODY_EVENT_REFRACTORY_SECONDS", "0.75"))
    posture_change_threshold_degrees: float = float(os.getenv("POSTURE_CHANGE_THRESHOLD_DEGREES", "12"))
    keypoint_confidence: float = float(os.getenv("KEYPOINT_CONFIDENCE", "0.35"))
    show_body_skeleton: bool = _bool_env("SHOW_BODY_SKELETON", True)
    landmark_profile: str = os.getenv("LANDMARK_PROFILE", "core_monitoring")
    face_display_groups: str = os.getenv("FACE_DISPLAY_GROUPS", "eyes,head_pose")
    face_measure_groups: str = os.getenv("FACE_MEASURE_GROUPS", "eyes,head_pose")
    body_display_groups: str = os.getenv("BODY_DISPLAY_GROUPS", "head_shoulders,torso")
    body_measure_groups: str = os.getenv("BODY_MEASURE_GROUPS", "head_shoulders,torso")
    feature_types: str = os.getenv("FEATURE_TYPES", "angle,frequency,normalized_movement")
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_max_bytes: int = int(os.getenv("LOG_MAX_BYTES", "5000000"))
    log_backup_count: int = int(os.getenv("LOG_BACKUP_COUNT", "3"))
    save_raw_video: bool = _bool_env("SAVE_RAW_VIDEO", False)
    auth_enabled: bool = _bool_env("AUTH_ENABLED", True)
    researcher_access_key: str = os.getenv("RESEARCHER_ACCESS_KEY", "")
    session_secret: str = os.getenv("SESSION_SECRET", "")
    auth_session_hours: int = int(os.getenv("AUTH_SESSION_HOURS", "8"))

    @property
    def mock_mode(self) -> bool:
        return self.app_mode == "mock"

    @staticmethod
    def csv_set(value: str) -> set[str]:
        return {item.strip() for item in value.split(",") if item.strip()}


settings = Settings()
