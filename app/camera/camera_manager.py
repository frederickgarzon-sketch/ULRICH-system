"""Threaded OpenCV camera capture with latest-frame buffering and reconnects."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import asdict, dataclass
from typing import Final

import cv2
import numpy as np

logger = logging.getLogger(__name__)

STATUS_OFFLINE: Final = "CAMERA OFFLINE"
STATUS_CONNECTING: Final = "CONNECTING"
STATUS_CONNECTED: Final = "CONNECTED"
STATUS_RECONNECTING: Final = "RECONNECTING"
STATUS_STOPPED: Final = "STOPPED"


def parse_camera_source(source: str | int) -> str | int:
    """Convert a numeric setting to an index while preserving stream/file URLs."""
    if isinstance(source, int):
        return source
    value = source.strip()
    if value.lstrip("-").isdigit():
        return int(value)
    return value


@dataclass(slots=True)
class CameraStats:
    name: str
    source: str
    status: str = STATUS_STOPPED
    capture_fps: float = 0.0
    frame_latency_ms: float = 0.0
    dropped_frames: int = 0
    failed_frames: int = 0
    width: int = 0
    height: int = 0
    last_error: str | None = None


class CameraManager:
    """Own one capture thread and retain only its newest frame."""

    def __init__(
        self,
        name: str,
        source: str | int,
        width: int,
        height: int,
        fps: int,
        reconnect_seconds: float = 2.0,
        failure_limit: int = 10,
    ) -> None:
        self.name = name
        self.source = parse_camera_source(source)
        self.requested_width = width
        self.requested_height = height
        self.requested_fps = fps
        self.reconnect_seconds = reconnect_seconds
        self.failure_limit = failure_limit
        self.stats = CameraStats(name=name, source=str(source))
        self._capture: cv2.VideoCapture | None = None
        self._frame: np.ndarray | None = None
        self._frame_time = 0.0
        self._frame_sequence = 0
        self._read_sequence = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._capture_loop, name=f"camera-{self.name}", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        self._release()
        self.stats.status = STATUS_STOPPED

    def latest_frame(self, copy: bool = True) -> tuple[np.ndarray | None, float, int]:
        with self._lock:
            frame = None if self._frame is None else (self._frame.copy() if copy else self._frame)
            sequence = self._frame_sequence
            captured_at = self._frame_time
            if sequence > self._read_sequence + 1:
                self.stats.dropped_frames += sequence - self._read_sequence - 1
            self._read_sequence = sequence
        if captured_at:
            self.stats.frame_latency_ms = round((time.monotonic() - captured_at) * 1000, 1)
        return frame, captured_at, sequence

    def status_payload(self) -> dict[str, object]:
        payload = asdict(self.stats)
        with self._lock:
            payload["frame_age_seconds"] = round(time.monotonic() - self._frame_time, 3) if self._frame_time else None
        return payload

    def _open(self) -> bool:
        self.stats.status = STATUS_CONNECTING if self.stats.failed_frames == 0 else STATUS_RECONNECTING
        try:
            backend = cv2.CAP_DSHOW if isinstance(self.source, int) else cv2.CAP_ANY
            capture = cv2.VideoCapture(self.source, backend)
            if not capture.isOpened():
                capture.release()
                self.stats.last_error = f"Unable to open source {self.source}"
                return False
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.requested_width)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.requested_height)
            capture.set(cv2.CAP_PROP_FPS, self.requested_fps)
            capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self._capture = capture
            self.stats.status = STATUS_CONNECTED
            self.stats.last_error = None
            logger.info("%s camera connected to %s", self.name, self.source)
            return True
        except Exception as exc:
            self.stats.last_error = str(exc)
            logger.exception("%s camera open failed", self.name)
            return False

    def _capture_loop(self) -> None:
        frame_count = 0
        fps_started = time.monotonic()
        consecutive_failures = 0
        while not self._stop.is_set():
            if self._capture is None and not self._open():
                self.stats.status = STATUS_OFFLINE
                self._stop.wait(self.reconnect_seconds)
                continue
            assert self._capture is not None
            ok, frame = self._capture.read()
            captured_at = time.monotonic()
            if not ok or frame is None:
                consecutive_failures += 1
                self.stats.failed_frames += 1
                if consecutive_failures >= self.failure_limit:
                    logger.warning("%s camera lost; reconnecting", self.name)
                    self.stats.status = STATUS_RECONNECTING
                    self._release()
                    consecutive_failures = 0
                    self._stop.wait(self.reconnect_seconds)
                else:
                    self._stop.wait(0.02)
                continue
            consecutive_failures = 0
            frame_count += 1
            with self._lock:
                self._frame = frame
                self._frame_time = captured_at
                self._frame_sequence += 1
            self.stats.height, self.stats.width = frame.shape[:2]
            elapsed = captured_at - fps_started
            if elapsed >= 1.0:
                self.stats.capture_fps = round(frame_count / elapsed, 1)
                frame_count = 0
                fps_started = captured_at
        self._release()

    def _release(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None


def discover_usb_cameras(max_index: int = 5,
                         skip_indexes: set[int] | None = None) -> list[dict[str, object]]:
    """Probe a small bounded set of Windows camera indexes."""
    found: list[dict[str, object]] = []
    skipped = skip_indexes or set()
    for index in range(max(0, min(max_index, 10))):
        if index in skipped:
            continue
        capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        try:
            if capture.isOpened():
                ok, frame = capture.read()
                found.append(
                    {
                        "index": index,
                        "available": bool(ok and frame is not None),
                        "width": int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
                        "height": int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                        "fps": round(capture.get(cv2.CAP_PROP_FPS), 1),
                        "in_use": False,
                    }
                )
        finally:
            capture.release()
    return found
