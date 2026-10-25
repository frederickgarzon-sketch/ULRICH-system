from app.camera.camera_manager import parse_camera_source
from app.camera.camera_system import CameraSystem, camera_system
from app.camera import camera_system as camera_module


def test_numeric_camera_sources_become_indexes() -> None:
    assert parse_camera_source("0") == 0
    assert parse_camera_source(" 2 ") == 2


def test_network_camera_sources_remain_strings() -> None:
    url = "http://raspberry-pi.local:8080/face-stream"
    assert parse_camera_source(url) == url


def test_mock_status_has_performance_fields() -> None:
    status = camera_system.status()
    assert status["mode"] == "mock"
    assert status["face"]["status"] == "MOCK"
    assert "capture_fps" in status["body"]


def test_real_duplicate_source_starts_only_one_reader(monkeypatch) -> None:
    fake_settings = type("Settings", (), {
        "mock_mode": False, "face_camera_source": "0", "body_camera_source": "0",
        "face_camera_width": 640, "face_camera_height": 480, "face_camera_fps": 20,
        "body_camera_width": 640, "body_camera_height": 480, "body_camera_fps": 20,
        "camera_reconnect_seconds": 2.0, "camera_failure_limit": 10,
    })()
    monkeypatch.setattr(camera_module, "settings", fake_settings)
    system = CameraSystem()
    started = []
    monkeypatch.setattr(system.face, "start", lambda: started.append("face"))
    monkeypatch.setattr(system.body, "start", lambda: started.append("body"))
    system.start()
    assert started == ["face"]
    assert system.body.stats.status == "CONFIGURATION CONFLICT"
