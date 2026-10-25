"""Environment-driven Raspberry Pi camera-node settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env.rpi")


def bool_env(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class NodeSettings:
    host: str = os.getenv("RPI_HOST", "0.0.0.0")
    port: int = int(os.getenv("RPI_PORT", "8090"))
    face_source: str = os.getenv("RPI_FACE_CAMERA_SOURCE", "0")
    body_source: str = os.getenv("RPI_BODY_CAMERA_SOURCE", "1")
    width: int = int(os.getenv("RPI_CAMERA_WIDTH", "1280"))
    height: int = int(os.getenv("RPI_CAMERA_HEIGHT", "720"))
    fps: int = int(os.getenv("RPI_CAMERA_FPS", "20"))
    jpeg_quality: int = int(os.getenv("RPI_JPEG_QUALITY", "75"))
    reconnect_seconds: float = float(os.getenv("RPI_RECONNECT_SECONDS", "2"))
    mock_mode: bool = bool_env("RPI_MOCK_MODE", False)


settings = NodeSettings()
