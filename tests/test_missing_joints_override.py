from types import SimpleNamespace
from app.services import calibration_service as service


def test_missing_joints_cannot_be_overridden(monkeypatch):
    monkeypatch.setattr(service, 'settings', SimpleNamespace(mock_mode=False, save_raw_video=False))
    monkeypatch.setattr(service, 'configuration_hash', lambda: 'test')
    monkeypatch.setattr(service.camera_system, 'status', lambda: {
        'face': {'status': 'CONNECTED', 'capture_fps': 20},
        'body': {'status': 'CONNECTED', 'capture_fps': 20}})
    monkeypatch.setattr(service.face_analysis_service, 'snapshot', lambda: {
        'tracking': True, 'calibrated': True, 'head_calibrated': True})
    body = {'tracking': True, 'person_count': 1, 'required_joints_visible': False}
    monkeypatch.setattr(service.body_analysis_service, 'snapshot', lambda: body)
    assert not service.readiness()['ready']
    assert not service.check_allowed({'passed': False, 'overridden': True})
    body['required_joints_visible'] = True
    assert service.readiness()['ready']
