"""Calibration wrap/stability and stale-value regressions without a camera."""
from app.services.face_analysis_service import FaceAnalysisService
from app.vision.head_pose import HeadPose


def test_wrapped_head_baseline_is_saved_near_180(monkeypatch):
    service = FaceAnalysisService()
    captured = {}
    monkeypatch.setattr(service, "_update_saved_calibration", lambda **data: captured.update(data))
    service._head_calibration_until = 1
    service._head_calibration_samples = [HeadPose(0, p, 0) for p in [179, -179] * 10]
    service._handle_head_calibration(HeadPose(0, 179, 0), 2)
    assert service.state.head_calibrated
    assert abs(captured["neutral_head"]["pitch"]) == 180
    assert service._head.update(HeadPose(0, 179, 0), 3).direction == "CENTER"


def test_moving_head_baseline_requires_retry(monkeypatch):
    service = FaceAnalysisService()
    captured = {}
    monkeypatch.setattr(service, "_update_saved_calibration", lambda **data: captured.update(data))
    service._head_calibration_until = 1
    service._head_calibration_samples = [HeadPose(y, 0, 0) for y in [-20, 20] * 10]
    service._handle_head_calibration(HeadPose(0, 0, 0), 2)
    assert not service.state.head_calibrated
    assert "hold your head still" in service.state.head_calibration_status
    assert not captured


def test_lost_pose_clears_old_angles_without_erasing_calibration():
    service = FaceAnalysisService()
    service.state.head_calibrated = True
    service.state.yaw, service.state.pitch, service.state.roll = 15, 0, 0
    service.state.head_direction = service.state.horizontal_direction = "RIGHT"
    service.state.head_movement_event = True
    service._clear_head_tracking()
    assert service.state.yaw is None and service.state.pitch is None and service.state.roll is None
    assert service.state.head_direction == service.state.horizontal_direction == "UNKNOWN"
    assert not service.state.head_movement_event
    assert service.state.head_calibrated
