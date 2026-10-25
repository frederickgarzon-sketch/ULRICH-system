from app.services.performance_health import evaluate_pipeline


def test_green_when_face_pipeline_is_within_target() -> None:
    result = evaluate_pipeline("face", {"status": "CONNECTED", "capture_fps": 25, "frame_latency_ms": 46},
                               {"tracking": True, "inference_ms": 30})
    assert result["level"] == "green"


def test_yellow_explains_degraded_face_fps() -> None:
    result = evaluate_pipeline("face", {"status": "CONNECTED", "capture_fps": 10, "frame_latency_ms": 40},
                               {"tracking": True, "inference_ms": 30})
    assert result["level"] == "yellow"
    assert "below target" in result["reason"]


def test_red_when_camera_offline_or_multiple_people() -> None:
    offline = evaluate_pipeline("face", {"status": "CAMERA OFFLINE", "capture_fps": 0, "frame_latency_ms": 0},
                                {"tracking": False, "inference_ms": 0})
    multiple = evaluate_pipeline("body", {"status": "CONNECTED", "capture_fps": 20, "frame_latency_ms": 20},
                                 {"tracking": True, "person_count": 2, "inference_ms": 40})
    assert offline["level"] == "red"
    assert multiple["level"] == "red"
    assert "Multiple people" in multiple["reason"]
