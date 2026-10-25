from app.services.calibration_service import configuration_hash
from app.config import settings
from dataclasses import replace
from app.services import calibration_service


def test_setup_fingerprint_is_stable_and_changes_with_camera_source(monkeypatch):
    original = configuration_hash()
    assert configuration_hash() == original
    monkeypatch.setattr(calibration_service, 'settings', replace(settings, face_camera_source='http://replacement.local/face'))
    assert configuration_hash() != original


def test_setup_fingerprint_changes_with_analysis_threshold(monkeypatch):
    original = configuration_hash()
    monkeypatch.setattr(calibration_service, 'settings', replace(settings, body_movement_threshold=settings.body_movement_threshold + 0.01))
    assert configuration_hash() != original
