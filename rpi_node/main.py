"""FastAPI MJPEG server for two USB cameras on Raspberry Pi 4B."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import asynccontextmanager

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from rpi_node.camera_node import NodeCamera
from rpi_node.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

common = (settings.width, settings.height, settings.fps, settings.reconnect_seconds)
face_camera = NodeCamera("face", settings.face_source, *common)
body_camera = NodeCamera("body", settings.body_source, *common)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not settings.mock_mode:
        face_camera.start()
        body_camera.start()
    logger.info("Camera node started in %s mode", "MOCK" if settings.mock_mode else "USB")
    yield
    face_camera.stop()
    body_camera.stop()


app = FastAPI(title="Behavioral Monitoring Camera Node", lifespan=lifespan, docs_url=None, redoc_url=None)


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "role": "camera-node", "mode": "mock" if settings.mock_mode else "usb",
            "face": status_for("face"), "body": status_for("body")}


@app.get("/stream/{camera_name}")
def stream(camera_name: str) -> StreamingResponse:
    if camera_name not in {"face", "body"}:
        raise HTTPException(status_code=404, detail="Unknown camera")
    return StreamingResponse(mjpeg(camera_name), media_type="multipart/x-mixed-replace; boundary=frame")


def status_for(camera_name: str) -> dict[str, object]:
    if settings.mock_mode:
        return {"name": camera_name, "source": "mock", "status": "MOCK", "fps": settings.fps,
                "width": settings.width, "height": settings.height, "failed_frames": 0, "last_error": None}
    return (face_camera if camera_name == "face" else body_camera).status()


def mjpeg(camera_name: str) -> Iterator[bytes]:
    camera = face_camera if camera_name == "face" else body_camera
    interval = 1 / max(settings.fps, 1)
    while True:
        frame = mock_frame(camera_name) if settings.mock_mode else camera.frame()
        if frame is None:
            frame = status_frame(camera_name, camera.state.status)
        elif frame.shape[1] != settings.width or frame.shape[0] != settings.height:
            # Some UVC cameras negotiate the nearest supported capture mode
            # (for example 320x240 for a requested 360x240). Normalize the
            # network stream to the researcher-selected processing dimensions.
            frame = cv2.resize(frame, (settings.width, settings.height), interpolation=cv2.INTER_AREA)
        ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, settings.jpeg_quality])
        if ok:
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + encoded.tobytes() + b"\r\n"
        time.sleep(interval)


def status_frame(name: str, status: str) -> np.ndarray:
    frame = np.zeros((settings.height, settings.width, 3), dtype=np.uint8)
    cv2.putText(frame, f"{name.upper()} CAMERA", (50, settings.height // 2 - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (230, 235, 240), 2)
    cv2.putText(frame, status, (50, settings.height // 2 + 35),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (80, 190, 255), 2)
    return frame


def mock_frame(name: str) -> np.ndarray:
    frame = status_frame(name, "RPi MOCK STREAM")
    color = (255, 190, 60) if name == "face" else (60, 220, 140)
    cv2.rectangle(frame, (20, 20), (settings.width - 20, settings.height - 20), color, 3)
    cv2.putText(frame, time.strftime("%H:%M:%S"), (50, settings.height - 55),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
    return frame
