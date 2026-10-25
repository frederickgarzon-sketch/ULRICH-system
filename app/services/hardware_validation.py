"""Read-only hardware readiness assessment for the final topology."""

from __future__ import annotations

from urllib.parse import urlsplit

from app.camera.camera_system import camera_system
from app.config import settings
from app.services.body_analysis_service import body_analysis_service
from app.services.face_analysis_service import face_analysis_service


def source_kind(source: str) -> str:
    value = str(source).lower()
    if value.startswith(("http://", "https://", "rtsp://")):
        return "network"
    if value.lstrip("-").isdigit():
        return "usb-index"
    return "device-path"


def node_health_url() -> str | None:
    sources = (str(settings.face_camera_source), str(settings.body_camera_source))
    network = [value for value in sources if source_kind(value) == "network"]
    if not network:
        return None
    parsed = urlsplit(network[0])
    return f"{parsed.scheme}://{parsed.netloc}/health"


def validation_report() -> dict[str, object]:
    cameras = camera_system.status()
    face = face_analysis_service.snapshot()
    body = body_analysis_service.snapshot()
    face_connected = cameras["face"]["status"] in {"CONNECTED", "MOCK"}
    body_connected = cameras["body"]["status"] in {"CONNECTED", "MOCK"}
    face_fps = float(cameras["face"]["capture_fps"])
    body_fps = float(cameras["body"]["capture_fps"])
    checks = [
        {"id": "real_mode", "label": "Real-camera mode", "passed": not settings.mock_mode,
         "detail": settings.app_mode.upper()},
        {"id": "face_camera", "label": "Face camera connected", "passed": face_connected,
         "detail": cameras["face"]["status"]},
        {"id": "body_camera", "label": "Body camera connected", "passed": body_connected,
         "detail": cameras["body"]["status"]},
        {"id": "face_fps", "label": "Face capture ≥ 10 FPS", "passed": face_fps >= 10,
         "detail": f"{face_fps} FPS"},
        {"id": "body_fps", "label": "Body capture ≥ 8 FPS", "passed": body_fps >= 8,
         "detail": f"{body_fps} FPS"},
        {"id": "face_worker", "label": "Face worker operational", "passed": face["status"] not in {"MODEL ERROR"},
         "detail": f"{face['status']} · {face['processing_fps']} FPS"},
        {"id": "body_model", "label": "YOLO Pose model ready", "passed": body["model_status"] in {"READY", "MOCK"},
         "detail": str(body["model_status"])},
        {"id": "privacy", "label": "Raw recording disabled", "passed": not settings.save_raw_video,
         "detail": "OFF" if not settings.save_raw_video else "ON"},
    ]
    passed = sum(bool(item["passed"]) for item in checks)
    return {
        "ready": passed == len(checks), "passed": passed, "total": len(checks), "checks": checks,
        "topology": "raspberry-pi" if node_health_url() else "direct-usb",
        "node_health_url": node_health_url(),
        "sources": {"face": {"value": settings.face_camera_source, "kind": source_kind(settings.face_camera_source)},
                    "body": {"value": settings.body_camera_source, "kind": source_kind(settings.body_camera_source)}},
        "cameras": cameras, "face_worker": face, "body_worker": body,
        "requires_physical_validation": [
            "Two-camera simultaneous capture", "Participant framing and calibration",
            "Camera unplug/reconnect", "Network interruption recovery",
            "Raspberry Pi reboot/autostart", "Sustained Ethernet throughput and Pi temperature",
        ],
    }
