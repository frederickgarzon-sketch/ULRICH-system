"""Application-level coordination for face and body camera inputs."""

from __future__ import annotations

import time
from collections.abc import Iterator

import cv2
import numpy as np

from app.camera.camera_manager import CameraManager
from app.config import settings


class CameraSystem:
    def __init__(self) -> None:
        common = {"reconnect_seconds": settings.camera_reconnect_seconds,
                  "failure_limit": settings.camera_failure_limit}
        self.face = CameraManager("face", settings.face_camera_source,
                                  settings.face_camera_width, settings.face_camera_height,
                                  settings.face_camera_fps, **common)
        self.body = CameraManager("body", settings.body_camera_source,
                                  settings.body_camera_width, settings.body_camera_height,
                                  settings.body_camera_fps, **common)
        self.source_conflict = (
            self.face.source == self.body.source
            and not settings.mock_mode
        )

    def start(self) -> None:
        if not settings.mock_mode:
            self.face.start()
            # Opening one physical capture device from two native OpenCV
            # threads can crash the Windows process. Keep the face preview
            # available for setup, but block the body reader until a distinct
            # device or stream is selected.
            if self.source_conflict:
                self.body.stats.status = "CONFIGURATION CONFLICT"
                self.body.stats.last_error = (
                    "Face and body use the same source. Select two different "
                    "USB cameras or the two Raspberry Pi stream URLs."
                )
            else:
                self.body.start()

    def stop(self) -> None:
        self.face.stop()
        self.body.stop()

    def status(self) -> dict[str, object]:
        if settings.mock_mode:
            mock = lambda name, source: {
                "name": name, "source": str(source), "status": "MOCK", "capture_fps": settings.camera_fps,
                "frame_latency_ms": 0.0, "dropped_frames": 0, "failed_frames": 0,
                "width": settings.camera_width, "height": settings.camera_height, "last_error": None,
            }
            face = mock("face", settings.face_camera_source)
            body = mock("body", settings.body_camera_source)
            face.update({"requested_width": settings.face_camera_width, "requested_height": settings.face_camera_height,
                         "requested_fps": settings.face_camera_fps})
            body.update({"requested_width": settings.body_camera_width, "requested_height": settings.body_camera_height,
                         "requested_fps": settings.body_camera_fps})
            return {"mode": "mock", "face": face, "body": body}
        face = self.face.status_payload(); body = self.body.status_payload()
        if self.source_conflict:
            body["status"] = "CONFIGURATION CONFLICT"
            body["last_error"] = (
                "Face and body use the same source. Select a different body camera."
            )
        face.update({"requested_width": self.face.requested_width, "requested_height": self.face.requested_height,
                     "requested_fps": self.face.requested_fps})
        body.update({"requested_width": self.body.requested_width, "requested_height": self.body.requested_height,
                     "requested_fps": self.body.requested_fps})
        return {"mode": "real", "face": face, "body": body,
                "source_conflict": self.source_conflict}

    def preview_stream(self, camera_name: str) -> Iterator[bytes]:
        manager = self.face if camera_name == "face" else self.body
        while True:
            if settings.mock_mode:
                frame = self._mock_frame(camera_name)
            else:
                frame, _, _ = manager.latest_frame()
                if frame is None:
                    frame = self._status_frame(camera_name, manager.stats.status)
            ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 78])
            if ok:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + encoded.tobytes() + b"\r\n"
            time.sleep(1 / min(settings.camera_fps, 15))

    @staticmethod
    def _status_frame(camera_name: str, status: str) -> np.ndarray:
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(frame, camera_name.upper() + " CAMERA", (42, 205), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (220, 230, 240), 2)
        cv2.putText(frame, status, (42, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (80, 180, 255), 2)
        return frame

    @classmethod
    def _mock_frame(cls, camera_name: str) -> np.ndarray:
        frame = cls._status_frame(camera_name, "DEMO / MOCK DATA")
        color = (255, 210, 80) if camera_name == "face" else (90, 230, 160)
        center = (320, 235)
        if camera_name == "face":
            cv2.circle(frame, center, 105, color, 4)
            cv2.circle(frame, (280, 215), 8, color, -1)
            cv2.circle(frame, (360, 215), 8, color, -1)
            cv2.ellipse(frame, (320, 265), (42, 20), 0, 0, 180, color, 3)
        else:
            cv2.circle(frame, (320, 155), 38, color, 4)
            cv2.line(frame, (320, 195), (320, 340), color, 5)
            cv2.line(frame, (320, 235), (235, 295), color, 5)
            cv2.line(frame, (320, 235), (405, 295), color, 5)
            cv2.line(frame, (320, 340), (260, 435), color, 5)
            cv2.line(frame, (320, 340), (380, 435), color, 5)
        return frame


camera_system = CameraSystem()
