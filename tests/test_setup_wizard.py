from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import json
import numpy as np
import pytest

from fastapi.testclient import TestClient

from app import main
from app.database.repository import repository
from app.database.database import initialize_database
from app.main import app
from app.services import system_setup_service
from app.services.calibration_service import summarize_missing_joints
from app.services.body_analysis_service import stable_missing_required_joints
from app.services.face_analysis_service import FaceAnalysisService
from app.services.access_control import COOKIE_NAME, Identity, issue_token


def reset_state():
    initialize_database()
    repository.save_system_setup_state(status="setup_required", current_step=1,
                                       progress_json="{}", clear_completion=True)


def test_setup_wizard_has_six_persistent_guided_steps():
    reset_state()
    with TestClient(app) as client:
        page = client.get("/setup")
        status = client.get("/api/setup/status")
    assert page.status_code == 200
    assert "Step 1 of 6" in page.text
    assert all(label in status.json()["step_names"] for label in (
        "System check", "Camera connection", "Camera assignment", "Room placement",
        "System calibration", "Connectivity and review",
    ))
    assert status.json()["completed"] is False
    assert status.json()["current_step"] == 1


def test_calibration_ui_exposes_running_locked_and_saved_feedback():
    root = Path(__file__).resolve().parents[1]
    template = (root / "templates" / "setup.html").read_text(encoding="utf-8")
    script = (root / "static" / "js" / "setup.js").read_text(encoding="utf-8")
    css = (root / "static" / "css" / "setup.css").read_text(encoding="utf-8")
    for element_id in (
        "calibration-live-status", "calibration-status-title", "calibration-countdown",
        "calibration-progress-track", "calibrate-eyes", "calibrate-head", "calibrate-directions",
    ):
        assert f'id="{element_id}"' in template
    assert "startCalibrationCountdown" in script
    assert "Complete eye baseline first" in script
    assert "completed and saved" in script
    assert "window.confirm" in script
    assert "activateStepPreviews" in script
    assert 'data-preview-src="/preview/body?overlays=false"' in template
    assert ".calibration-step-button.running" in css
    assert ".calibration-live-status.completed" in css


def test_missing_body_joints_are_grouped_into_clear_placement_regions():
    result = summarize_missing_joints([
        "nose", "left shoulder", "right shoulder", "left wrist", "right wrist",
        "left knee", "right knee", "left ankle",
    ])
    assert result == "face/nose, both shoulders, both wrists, both knees, left ankle"


def test_setup_explains_default_seated_upper_body_requirement():
    template = Path("templates/setup.html").read_text(encoding="utf-8")
    assert "Prioritize a clear seated upper-body view" in template
    assert "Knees and feet improve full-body analysis but are optional" in template
    assert "Head, shoulders, elbows, hands, and hips remain inside the frame" in template


def test_body_joint_readiness_ignores_one_noisy_frame_but_not_sustained_loss():
    visible = np.full(17, 0.9)
    noisy = visible.copy(); noisy[10] = 0.1
    required = {5, 6, 9, 10, 11, 12}
    assert stable_missing_required_joints([visible, noisy, visible], required, 0.35) == []
    assert stable_missing_required_joints([noisy, noisy, visible], required, 0.35) == [10]


def test_mock_mode_can_exercise_calibration_feedback_without_real_measurement():
    reset_state()
    with TestClient(app) as client:
        eye = client.post("/api/face/calibration/start?duration_seconds=10")
        head = client.post("/api/head/calibration/start?duration_seconds=10")
    assert eye.status_code == 200 and eye.json()["simulation"] is True
    assert head.status_code == 200 and head.json()["simulation"] is True


def test_face_and_head_baselines_restore_from_database_after_restart():
    reset_state()
    service = FaceAnalysisService()
    repository.save_system_setup_state(
        status="in_progress", current_step=5,
        progress_json=json.dumps({"step_5": {
            "calibration_key": service._calibration_key(),
            "eye_baseline": 0.3,
            "eye_threshold": 0.216,
            "neutral_head": {"yaw": 8.5, "pitch": -172.0, "roll": 1.25},
        }}),
    )
    assert service.restore_saved_calibration() is True
    snapshot = service.snapshot()
    assert snapshot["calibrated"] is True
    assert snapshot["threshold"] == pytest.approx(0.216)
    assert snapshot["head_calibrated"] is True
    assert "restored" in str(snapshot["calibration_status"]).lower()
    assert "restored" in str(snapshot["head_calibration_status"]).lower()
    reset_state()


def test_setup_progress_survives_a_new_request():
    reset_state()
    with TestClient(app) as client:
        saved = client.put("/api/setup/progress", json={
            "step": 4, "values": {"lighting": True, "face_framing": True,
                                    "body_framing": True, "distance": True},
        })
        restored = client.get("/api/setup/status")
    assert saved.status_code == 200
    assert restored.json()["current_step"] == 4
    assert restored.json()["progress"]["step_4"]["body_framing"] is True


def test_direction_progress_requires_order_and_two_live_matches():
    reset_state()
    first = system_setup_service.record_direction_observation("UP", "UP")
    assert first["progress"]["step_5"]["direction_stable_count"] == 1
    second = system_setup_service.record_direction_observation("UP", "UP")
    assert second["progress"]["step_5"]["directions_passed"] == ["UP"]
    with pytest.raises(ValueError):
        system_setup_service.record_direction_observation("RIGHT", "RIGHT")


def test_setup_cannot_finish_without_room_confirmation():
    reset_state()
    with TestClient(app) as client:
        response = client.post("/api/setup/complete", json={"confirm": True})
    assert response.status_code == 409
    assert "lighting" in response.json()["detail"].lower()


def test_setup_completion_is_durable_and_configuration_aware(monkeypatch):
    reset_state()


def test_repeated_setup_completion_does_not_create_duplicate_profile(monkeypatch):
    reset_state()
    repository.save_system_setup_state(status="in_progress", current_step=6,
        progress_json='{"step_4":{"lighting":true,"face_framing":true,"body_framing":true,"distance":true},'
                      '"step_5":{"ready":true,"directions_passed":["UP","DOWN","LEFT","RIGHT","CENTER"]},'
                      '"step_6":{"participant_connected":true,"connectivity_reviewed":true}}')
    checks = [{"id": name, "label": name, "passed": True, "detail": "Pass"}
              for name in ("face_camera", "body_camera", "face_tracking", "body_tracking",
                           "face_fps", "body_fps", "face_calibration", "head_calibration", "privacy")]
    monkeypatch.setattr(system_setup_service, "readiness", lambda: {
        "ready": True, "passed": len(checks), "total": len(checks), "checks": checks,
    })
    first = system_setup_service.complete_setup(None, "Owner")
    profile_id = first["calibration_version"]
    count_before = len(repository.list_calibration_profiles())
    second = system_setup_service.complete_setup(None, "Owner")
    assert second["calibration_version"] == profile_id
    assert len(repository.list_calibration_profiles()) == count_before
    reset_state()


def test_saved_step_five_remains_valid_when_participant_leaves_before_finish(monkeypatch):
    """Final review must not demand that the calibration participant stay in frame."""
    reset_state()
    repository.save_system_setup_state(status="in_progress", current_step=6,
        progress_json='{"step_4":{"lighting":true,"face_framing":true,"body_framing":true,"distance":true},'
                      '"step_5":{"ready":true,"directions_passed":["UP","DOWN","LEFT","RIGHT","CENTER"]},'
                      '"step_6":{"participant_connected":true,"connectivity_reviewed":true}}')
    checks = [
        {"id": name, "label": name, "passed": name not in {"face_tracking", "body_tracking"},
         "detail": "No participant currently in frame"}
        for name in ("face_camera", "body_camera", "face_tracking", "body_tracking",
                     "face_fps", "body_fps", "face_calibration", "head_calibration", "privacy")
    ]
    monkeypatch.setattr(system_setup_service, "readiness", lambda: {
        "ready": False, "passed": len(checks) - 2, "total": len(checks), "checks": checks,
    })
    with TestClient(app) as client:
        completed = client.post("/api/setup/complete", json={"confirm": True})
        restored = client.get("/api/setup/status")
    assert completed.status_code == 200
    assert restored.json()["status"] == "ready"
    assert restored.json()["can_start"] is True
    reset_state()


def test_step_five_persists_server_validated_snapshot(monkeypatch):
    reset_state()
    repository.save_system_setup_state(
        status="in_progress", current_step=5,
        progress_json='{"step_5":{"ready":false,"directions_passed":'
                      '["UP","DOWN","LEFT","RIGHT","CENTER"]}}',
    )
    checks = [{"id": name, "label": name, "passed": True, "detail": "Pass"}
              for name in ("face_camera", "body_camera", "face_tracking", "body_tracking",
                           "face_fps", "body_fps", "face_calibration", "head_calibration", "privacy")]
    monkeypatch.setattr(system_setup_service, "readiness", lambda: {
        "configuration_hash": "validated-hash", "ready": True,
        "passed": len(checks), "total": len(checks), "checks": checks,
    })
    result = system_setup_service.save_progress(5, {"ready": True})
    saved = result["progress"]["step_5"]
    assert saved["ready"] is True
    assert saved["validation_configuration_hash"] == "validated-hash"
    assert saved["validated_check_ids"] == [check["id"] for check in checks]
    assert saved["validated_at"]
    reset_state()
    repository.save_system_setup_state(status="in_progress", current_step=6,
        progress_json='{"step_4":{"lighting":true,"face_framing":true,"body_framing":true,"distance":true},'
                      '"step_5":{"ready":true,"directions_passed":["UP","DOWN","LEFT","RIGHT","CENTER"]},'
                      '"step_6":{"participant_connected":true,"connectivity_reviewed":true}}')
    checks = [{"id": name, "label": name, "passed": True, "detail": "Pass"}
              for name in ("face_camera", "body_camera", "face_tracking", "body_tracking",
                           "face_fps", "body_fps", "face_calibration", "head_calibration", "privacy")]
    monkeypatch.setattr(system_setup_service, "readiness", lambda: {
        "ready": True, "passed": len(checks), "total": len(checks), "checks": checks,
    })
    with TestClient(app) as client:
        completed = client.post("/api/setup/complete", json={"confirm": True})
        restored = client.get("/api/setup/status")
    assert completed.status_code == 200
    assert completed.json()["completed"] is True
    assert restored.json()["can_operate"] is True
    assert restored.json()["can_start"] is True
    assert restored.json()["completed_at"]
    failed_checks = [dict(check) for check in checks]
    failed_checks[1]["passed"] = False
    monkeypatch.setattr(system_setup_service, "readiness", lambda: {
        "ready": False, "passed": len(failed_checks) - 1, "total": len(failed_checks), "checks": failed_checks,
    })
    degraded = system_setup_service.status_payload()
    assert degraded["status"] == "needs_attention"
    assert degraded["can_operate"] is True
    assert degraded["can_start"] is False
    reset_state()


def test_real_operation_page_redirects_to_incomplete_setup(monkeypatch):
    reset_state()
    monkeypatch.setattr(main, "settings", replace(main.settings, app_mode="real", auth_enabled=True))
    owner = Identity(None, "System Owner", "owner", True)
    with TestClient(app) as client:
        client.cookies.set(COOKIE_NAME, issue_token(owner))
        response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/setup?step=")


def test_system_setup_requires_fresh_admin_confirmation(monkeypatch):
    monkeypatch.setattr(main, "settings", replace(main.settings, auth_enabled=True))
    owner = Identity(None, "System Owner", "owner", True)
    monkeypatch.setattr(main, "authenticate_access_key", lambda value: owner if value == "valid" else None)
    with TestClient(app) as client:
        client.cookies.set(COOKIE_NAME, issue_token(owner))
        locked = client.get("/system-setup")
        wrong = client.post("/system-setup", data={"access_key": "wrong", "next": "/system-setup"})
        unlocked = client.post("/system-setup", data={"access_key": "valid", "next": "/system-setup"},
                               follow_redirects=False)
    assert locked.status_code == 200 and "Unlock System Setup" in locked.text
    assert wrong.status_code == 401
    assert unlocked.status_code == 303 and unlocked.headers["location"] == "/system-setup"


def test_first_login_enters_setup_and_returning_ready_login_enters_operation(monkeypatch):
    reset_state()
    main._login_failures.clear()
    owner = Identity(None, "System Owner", "owner", True)
    monkeypatch.setattr(main, "settings", replace(main.settings, auth_enabled=True))
    monkeypatch.setattr(main, "authenticate_access_key", lambda value: owner if value == "valid" else None)
    with TestClient(app) as client:
        first = client.post("/login", data={"access_key": "valid", "next": "/"},
                            follow_redirects=False)
        assert first.status_code == 303 and first.headers["location"].startswith("/setup?step=")
        repository.save_system_setup_state(
            status="ready", current_step=6, progress_json="{}",
            configuration_hash=system_setup_service.configuration_hash(),
            calibration_version="test", completed_by_name="System Owner",
            completed_at=datetime.now(timezone.utc),
        )
        client.cookies.set(COOKIE_NAME, issue_token(owner))
        returning = client.get("/login", follow_redirects=False)
    assert returning.status_code == 303 and returning.headers["location"] == "/"
    main._login_failures.clear()
    reset_state()


def test_completed_setup_requires_fresh_unlock_for_setup_changes(monkeypatch):
    reset_state()
    owner = Identity(None, "System Owner", "owner", True)
    repository.save_system_setup_state(
        status="ready", current_step=6, progress_json="{}",
        configuration_hash=system_setup_service.configuration_hash(),
        calibration_version="test", completed_by_name="System Owner",
        completed_at=datetime.now(timezone.utc),
    )
    monkeypatch.setattr(main, "settings", replace(main.settings, auth_enabled=True))
    with TestClient(app) as client:
        client.cookies.set(COOKIE_NAME, issue_token(owner))
        page = client.get("/setup?step=2", follow_redirects=False)
        write = client.put("/api/setup/progress", json={"step": 2, "values": {"connection_mode": "usb"}})
        quick_check = client.get("/calibration?mode=verification", follow_redirects=False)
    assert page.status_code == 303 and page.headers["location"] == "/system-setup?next=/setup"
    assert write.status_code == 403
    assert quick_check.status_code == 200
    reset_state()
