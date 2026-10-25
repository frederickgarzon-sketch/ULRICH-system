"""Bounded latest-frame USB capture for the Raspberry Pi node."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import asdict, dataclass

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def parse_source(value: str) -> str | int:
    stripped = value.strip()
    return int(stripped) if stripped.isdigit() else stripped


@dataclass(slots=True)
class NodeCameraStatus:
    name: str
    source: str
    status: str = "STOPPED"
    fps: float = 0.0
    width: int = 0
    height: int = 0
    failed_frames: int = 0
    last_error: str | None = None


class NodeCamera:
    def __init__(self, name: str, source: str, width: int, height: int, fps: int, reconnect_seconds: float) -> None:
        self.name = name
        self.source = parse_source(source)
        self.requested_width = width
        self.requested_height = height
        self.requested_fps = fps
        self.reconnect_seconds = reconnect_seconds
        self.state = NodeCameraStatus(name, source)
        self._capture: cv2.VideoCapture | None = None
        self._frame: np.ndarray | None = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name=f"rpi-{self.name}", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        self._release()
        self.state.status = "STOPPED"

    def frame(self) -> np.ndarray | None:
        with self._lock:
            return None if self._frame is None else self._frame.copy()

    def status(self) -> dict[str, object]:
        return asdict(self.state)

    def _open(self) -> bool:
        self.state.status = "RECONNECTING"
        capture = cv2.VideoCapture(self.source)
        if not capture.isOpened():
            capture.release()
            self.state.last_error = f"Unable to open {self.source}"
            self.state.status = "CAMERA OFFLINE"
            return False
        # Two 720p YUYV feeds can saturate the Pi 4 USB bus. Request the
        # webcams' hardware MJPEG mode before setting resolution/FPS.
        capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.requested_width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.requested_height)
        capture.set(cv2.CAP_PROP_FPS, self.requested_fps)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self._capture = capture
        self.state.status = "CONNECTED"
        self.state.last_error = None
        logger.info("%s camera connected to %s", self.name, self.source)
        return True

    def _loop(self) -> None:
        count, fps_started = 0, time.monotonic()
        while not self._stop.is_set():
            if self._capture is None and not self._open():
                self._stop.wait(self.reconnect_seconds)
                continue
            assert self._capture is not None
            ok, frame = self._capture.read()
            if not ok or frame is None:
                self.state.failed_frames += 1
                self.state.status = "RECONNECTING"
                self._release()
                self._stop.wait(self.reconnect_seconds)
                continue
            with self._lock:
                self._frame = frame
            self.state.height, self.state.width = frame.shape[:2]
            count += 1
            elapsed = time.monotonic() - fps_started
            if elapsed >= 1:
                self.state.fps = round(count / elapsed, 1)
                count, fps_started = 0, time.monotonic()
        self._release()

    def _release(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None
