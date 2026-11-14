import json
from dataclasses import replace

from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.database.repository import repository
from app.tasks.attention_task import attention_task_service
from app.services.access_control import COOKIE_NAME, Identity, issue_token, token_hash, valid_token
from app.services.access_control import decrypt_recoverable_pin
from app.api import routes


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["raw_video_recording"] is False


def test_guided_workflow_has_one_ordered_source_of_truth() -> None:
    with TestClient(app) as client:
        response = client.get("/api/workflow/status")
    assert response.status_code == 200
    data = response.json()
    assert [step["id"] for step in data["steps"]] == [
        "cameras", "room", "participant", "session", "activity", "results"
    ]
    assert data["current_step"] in {step["id"] for step in data["steps"]}
    assert data["next_action"]["href"].startswith("/")


def test_login_page_has_project_specific_access_form() -> None:
    with TestClient(app) as client:
        response = client.get("/login")
    assert response.status_code == 200
    assert "Behavior Monitor" in response.text
    assert "/static/img/brand/behavior-monitor-icon.png" in response.text
    assert "Main-server access key" in response.text
    assert "Open session console" in response.text
    assert 'id="show-key"' in response.text


def test_login_is_rate_limited_after_five_failures() -> None:
    with TestClient(app) as client:
        responses = [client.post("/login", data={"access_key": f"wrong-{index}", "next": "/"})
                     for index in range(6)]
    assert all(item.status_code == 401 for item in responses[:5])
    assert responses[5].status_code == 429


def test_final_brand_assets_are_served() -> None:
    with TestClient(app) as client:
        icon = client.get("/static/img/brand/behavior-monitor-icon.png")
        lockup = client.get("/static/img/brand/behavior-monitor-lockup.png")
        dashboard = client.get("/")
    assert icon.status_code == 200 and icon.headers["content-type"] == "image/png"
    assert lockup.status_code == 200 and lockup.headers["content-type"] == "image/png"
    assert "Behavior Monitor" in dashboard.text


def test_dashboard_loads() -> None:
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "DEMO / MOCK DATA" not in response.text
    assert 'id="system-mode"' in response.text and "LIVE" in response.text
    assert "Research session overview" in response.text
    assert "A silent 2-second camera and framing check runs automatically." in response.text
    assert 'id="operation-check"' not in response.text
    assert "Quick readiness check" not in response.text


def _accepted_system_profile_for_automatic_start(client: TestClient):
    profile = repository.latest_accepted_calibration_type("system")
    if profile is not None:
        return profile
    created = client.post("/api/calibration/profiles", json={
        "name": "Automatic start test setup", "profile_type": "system",
        "manual_checks": {"camera_roles": True, "lighting": True,
                          "face_framing": True, "body_framing": True,
                          "participant_position": True},
    }).json()
    assert client.post(f"/api/calibration/profiles/{created['id']}/accept").status_code == 200
    return repository.latest_accepted_calibration_type("system")


def _automatic_check(passed: bool = True) -> dict[str, object]:
    identifiers = ("face_camera", "body_camera", "face_tracking", "body_tracking",
                   "face_fps", "body_fps", "face_calibration", "head_calibration", "privacy")
    return {"checks": [{"id": identifier, "label": identifier.replace("_", " ").title(),
                         "passed": passed if identifier == "body_tracking" else True,
                         "detail": "TRACKING" if passed or identifier != "body_tracking" else "0 people · NO PERSON"}
                        for identifier in identifiers]}


def test_session_start_runs_automatic_check_without_manual_participant_verification(monkeypatch) -> None:
    with TestClient(app) as client:
        profile = _accepted_system_profile_for_automatic_start(client)
        participant = client.post("/api/participants", json={"participant_code": "AUTO_START_OK"}).json()
        monkeypatch.setattr(routes, "settings", replace(settings, app_mode="real"))
        monkeypatch.setattr(routes, "configuration_hash", lambda: profile.configuration_hash)
        monkeypatch.setattr(routes, "calibration_readiness", lambda: _automatic_check(True))
        monkeypatch.setattr(routes.time, "sleep", lambda _seconds: None)
        started = client.post("/api/sessions/start", json={"participant_id": participant["id"]})
        assert started.status_code == 201
        verification = repository.latest_passing_verification(participant["id"])
        assert verification is not None
        saved = json.loads(verification.checks_json)
        assert saved["automatic"] is True and saved["duration_seconds"] == 2.0
        client.post(f"/api/sessions/{started.json()['id']}/stop", json={})


def test_session_start_returns_focused_camera_action_when_automatic_check_fails(monkeypatch) -> None:
    with TestClient(app) as client:
        profile = _accepted_system_profile_for_automatic_start(client)
        participant = client.post("/api/participants", json={"participant_code": "AUTO_START_FAIL"}).json()
        monkeypatch.setattr(routes, "settings", replace(settings, app_mode="real"))
        monkeypatch.setattr(routes, "configuration_hash", lambda: profile.configuration_hash)
        monkeypatch.setattr(routes, "calibration_readiness", lambda: _automatic_check(False))
        monkeypatch.setattr(routes.time, "sleep", lambda _seconds: None)
        blocked = client.post("/api/sessions/start", json={"participant_id": participant["id"]})
        assert blocked.status_code == 409
        assert "Body Tracking needs attention" in blocked.json()["detail"]
        assert client.get("/api/sessions/active").json()["active"] is False


def test_primary_navigation_uses_dedicated_pages() -> None:
    with TestClient(app) as client:
        overview = client.get("/")
        live = client.get("/live-monitor")
        attention = client.get("/attention")
        records = client.get("/records")
    assert all(response.status_code == 200 for response in (overview, live, attention, records))
    assert 'href="/live-monitor"' in overview.text
    assert 'id="camera-grid"' not in overview.text
    assert 'id="camera-grid"' in live.text and "Research session overview" not in live.text
    assert "Configure &amp; launch" in attention.text
    assert 'href="/attention-task/operator"' in attention.text
    assert 'id="session-history"' in records.text and 'id="session-history"' not in overview.text


def test_named_account_six_digit_pin_is_visible_replaceable_and_revocable() -> None:
    with TestClient(app) as client:
        created = client.post("/api/users", json={
            "full_name": "Test Operator", "professional_title": "Teacher",
            "organization": "Test School", "role": "operator", "expires_in_days": 7,
        })
        assert created.status_code == 201
        payload = created.json()
        assert payload["access_token"].isdigit() and len(payload["access_token"]) == 6
        listed = client.get("/api/users").json()
        account = next(item for item in listed if item["id"] == payload["id"])
        assert account["access_token"] == payload["access_token"]
        stored = repository.get_user_account(payload["id"])
        assert stored.access_pin.startswith("enc:v1:")
        assert decrypt_recoverable_pin(stored.access_pin) == payload["access_token"]
        replaced = client.post(f"/api/users/{payload['id']}/regenerate-token")
        assert replaced.status_code == 200
        assert replaced.json()["access_token"].isdigit()
        assert replaced.json()["access_token"] != payload["access_token"]
        revoked = client.post(f"/api/users/{payload['id']}/status?active=false")
    assert revoked.status_code == 200 and revoked.json()["active"] is False


def test_admin_can_delete_empty_account_but_not_account_with_records() -> None:
    with TestClient(app) as client:
        empty = client.post("/api/users", json={
            "full_name": "Temporary Empty Account", "role": "operator", "expires_in_days": 1}).json()
        deleted = client.delete(f"/api/users/{empty['id']}?confirm=true")
        owned = client.post("/api/users", json={
            "full_name": "Account With Records", "role": "operator", "expires_in_days": 1}).json()
        account = repository.get_user_account(owned["id"])
        client.cookies.set(COOKIE_NAME, issue_token(Identity(account.id, account.full_name, account.role)))
        participant = client.post("/api/participants", json={"participant_code": "DELETE_GUARD"})
        client.cookies.clear()
        blocked = client.delete(f"/api/users/{owned['id']}?confirm=true")
    assert deleted.status_code == 204
    assert participant.status_code == 201
    assert blocked.status_code == 409


def test_extended_participant_profile_round_trip() -> None:
    with TestClient(app) as client:
        created = client.post("/api/participants", json={
            "participant_code": "PROFILE_TEST", "display_name": "Sample Participant",
            "date_of_birth": "2015-06-12", "sex": "Male", "grade_level": "Grade 5",
            "school_site": "Study Site A", "guardian_name": "Guardian",
            "consent_reference": "CONSENT-001", "consent_date": "2026-09-18",
            "diagnosis_status": "under_assessment", "accommodations": "Short instructions",
        })
        assert created.status_code == 201
        updated = client.put(f"/api/participants/{created.json()['id']}", json={
            "display_name": "Updated Participant", "research_notes": "Practice completed",
        })
    assert updated.status_code == 200
    assert updated.json()["research_notes"] == "Practice completed"


def test_participant_update_rejects_invalid_research_profile_values() -> None:
    with TestClient(app) as client:
        created = client.post("/api/participants", json={"participant_code": "PROFILE_VALIDATE"})
        participant_id = created.json()["id"]
        invalid_date = client.put(f"/api/participants/{participant_id}", json={"date_of_birth": "06/12/2015"})
        invalid_status = client.put(f"/api/participants/{participant_id}", json={"diagnosis_status": "confirmed_by_app"})
    assert invalid_date.status_code == 422
    assert invalid_status.status_code == 422


def test_standard_users_cannot_view_each_others_participants() -> None:
    first = repository.create_user_account(full_name="Operator One", organization=None,
        professional_title="Teacher", role="operator", token_hash=token_hash("one"),
        token_hint="ONE1", expires_at=None)
    second = repository.create_user_account(full_name="Operator Two", organization=None,
        professional_title="Teacher", role="operator", token_hash=token_hash("two"),
        token_hint="TWO2", expires_at=None)
    with TestClient(app) as client:
        client.cookies.set(COOKIE_NAME, issue_token(Identity(first.id, first.full_name, first.role)))
        created = client.post("/api/participants", json={"participant_code": "OWNED_ONE"})
        assert created.status_code == 201
        client.cookies.set(COOKIE_NAME, issue_token(Identity(second.id, second.full_name, second.role)))
        visible = client.get("/api/participants").json()
        forbidden = client.put(f"/api/participants/{created.json()['id']}", json={"display_name": "No access"})
    assert all(item["participant_code"] != "OWNED_ONE" for item in visible)
    assert forbidden.status_code == 403


def test_security_headers_are_present() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cache-control"] == "no-store"


def test_cross_site_state_change_is_blocked() -> None:
    with TestClient(app) as client:
        response = client.post("/api/attention/abort", headers={
            "Origin": "https://untrusted.example", "Sec-Fetch-Site": "cross-site"})
    assert response.status_code == 403


def test_equivalent_loopback_origin_is_allowed_for_logout() -> None:
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        response = client.post("/logout", headers={
            "Origin": "http://localhost:8000", "Sec-Fetch-Site": "same-site"},
            follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_same_origin_browser_form_survives_local_origin_rewrite() -> None:
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        response = client.post("/login", data={"access_key": "invalid-probe"}, headers={
            "Origin": "http://local-proxy.invalid:8000", "Sec-Fetch-Site": "same-origin"},
            follow_redirects=False)
    # The request must reach login, not fail as a JSON origin error.
    assert response.status_code in {401, 429}
    assert "text/html" in response.headers["content-type"]


def test_login_is_not_blocked_when_local_browser_rewrites_origin() -> None:
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        response = client.post("/login", data={"access_key": "invalid-probe"}, headers={
            "Origin": "http://untrusted.invalid:8000"}, follow_redirects=False)
    assert response.status_code in {401, 429}
    assert "text/html" in response.headers["content-type"]


def test_production_auth_keeps_participant_capability_public_but_operator_private() -> None:
    pairing = attention_task_service.pair_display()
    original = settings.auth_enabled
    object.__setattr__(settings, "auth_enabled", True)
    try:
        with TestClient(app) as client:
            dashboard = client.get("/", follow_redirects=False)
            operator = client.get("/attention-task/operator", follow_redirects=False)
            participant = client.get(f"/attention-task?token={pairing['token']}", follow_redirects=False)
            status = client.get(f"/api/participant-task/status?token={pairing['token']}")
        assert dashboard.status_code == 303 and dashboard.headers["location"].startswith("/login")
        assert operator.status_code == 303 and operator.headers["location"].startswith("/login")
        assert participant.status_code == 200
        assert status.status_code == 200
    finally:
        object.__setattr__(settings, "auth_enabled", original)


def test_legacy_attention_operator_query_redirects_to_operator_console() -> None:
    with TestClient(app) as client:
        response = client.get("/attention-task?operator=", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/attention-task/operator"


def test_oversized_request_is_rejected() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/participants", content=b"x", headers={"content-length": "1000001", "content-type": "application/json"}
        )
    assert response.status_code == 413


def test_system_status_reports_device_and_versions() -> None:
    with TestClient(app) as client:
        response = client.get("/api/system/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ai_device"] in {"CPU", "CUDA"}
    assert payload["raw_video_recording"] is False
    assert "fastapi" in payload["versions"]


def test_settings_page_and_api_load() -> None:
    with TestClient(app) as client:
        page = client.get("/settings")
        response = client.get("/api/settings")
    assert page.status_code == 200
    assert "Settings &amp; Calibration" in page.text or "Settings & Calibration" in page.text
    assert "Landmark &amp; Feature Profile" in page.text or "Landmark & Feature Profile" in page.text
    assert "Mock/demo" not in page.text
    assert 'name="app_mode"' not in page.text
    assert response.status_code == 200
    assert response.json()["settings"]["save_raw_video"] is False


def test_guided_calibration_page_and_readiness_load() -> None:
    with TestClient(app) as client:
        page = client.get("/calibration")
        response = client.get("/api/calibration/readiness")
    assert page.status_code == 200
    assert "Guided calibration" in page.text
    assert "Guided face calibration" in page.text
    assert 'id="coach-timer"' in page.text
    assert 'id="start-directions"' in page.text
    assert "/static/css/calibration-compact.css" not in page.text
    assert "/static/css/calibration-v2.css" in page.text
    assert "Review and save" in page.text
    payload = response.json()
    assert response.status_code == 200
    assert payload["total"] == len(payload["checks"])
    assert any(item["id"] == "privacy" for item in payload["checks"])


def test_dashboard_calibration_gate_status_is_explicit() -> None:
    with TestClient(app) as client:
        dashboard = client.get("/")
        status = client.get("/api/calibration/status")
    assert dashboard.status_code == 200
    assert "dashboard.js" in dashboard.text
    assert status.status_code == 200
    payload = status.json()
    assert {"ready", "system_ready", "participant_baseline_ready",
            "session_verification_ready", "next_step", "message"} <= payload.keys()


def test_calibration_profile_lifecycle_and_accepted_lock() -> None:
    manual_checks = {
        "lighting": True, "face_framing": True, "body_framing": True,
        "participant_position": True, "camera_roles": True,
    }
    with TestClient(app) as client:
        created = client.post("/api/calibration/profiles", json={
            "name": "Automated calibration test", "participant_id": None,
            "manual_checks": manual_checks, "notes": "Test profile",
        })
        assert created.status_code == 201
        profile_id = created.json()["id"]
        accepted = client.post(f"/api/calibration/profiles/{profile_id}/accept")
        refused = client.delete(f"/api/calibration/profiles/{profile_id}?confirm=true")
        fetched = client.get(f"/api/calibration/profiles/{profile_id}")
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"
    assert refused.status_code == 409
    assert fetched.json()["configuration_hash"]


def test_operator_calibration_scope_and_quick_verification() -> None:
    account = repository.create_user_account(full_name="Calibration Operator", organization=None,
        professional_title="Teacher", role="operator", token_hash=token_hash("cal-op"),
        token_hint="CAL1", expires_at=None)
    checks = {"lighting": True, "face_framing": True, "body_framing": True,
              "participant_position": True, "camera_roles": True}
    with TestClient(app) as client:
        room = client.post("/api/calibration/profiles", json={
            "name": "Operator test room", "profile_type": "system", "manual_checks": checks})
        assert room.status_code == 201
        assert client.post(f"/api/calibration/profiles/{room.json()['id']}/accept").status_code == 200
        client.cookies.set(COOKIE_NAME, issue_token(Identity(account.id, account.full_name, account.role)))
        participant = client.post("/api/participants", json={"participant_code": "CAL_SCOPE"}).json()
        operator_room = client.post("/api/calibration/profiles", json={
            "name": "Room setup", "profile_type": "system", "manual_checks": checks})
        operator_accept = client.post(f"/api/calibration/profiles/{operator_room.json()['id']}/accept")
        operator_delete = client.delete(f"/api/calibration/profiles/{operator_room.json()['id']}?confirm=true")
        legacy_baseline = client.post("/api/calibration/profiles", json={
            "name": "Participant baseline", "profile_type": "participant",
            "participant_id": participant["id"], "manual_checks": checks})
        verified = client.post("/api/calibration/verify", json={
            "participant_id": participant["id"], "face_visible": True, "distance_ok": True,
            "body_visible": True, "lighting_ok": True})
    assert operator_room.status_code == 201
    assert operator_accept.status_code == 200
    assert operator_delete.status_code == 403
    assert legacy_baseline.status_code == 422
    assert verified.status_code == 201 and verified.json()["passed"] is True
    assert verified.json()["valid_for_minutes"] == 15


def test_settings_api_refuses_raw_video_enable() -> None:
    with TestClient(app) as client:
        current = client.get("/api/settings").json()["settings"]
        current["save_raw_video"] = True
        response = client.put("/api/settings", json=current)
    assert response.status_code == 422


def test_settings_allow_overlay_only_face_groups_but_refuse_measurement() -> None:
    with TestClient(app) as client:
        current = client.get("/api/settings").json()["settings"]
        current["face_display_groups"] = "eyes,head_pose,iris,mouth,face_contour"
        display_response = client.put("/api/settings", json=current)
        current["face_measure_groups"] = "eyes,head_pose,iris"
        measure_response = client.put("/api/settings", json=current)
    assert display_response.status_code == 200
    assert measure_response.status_code == 422
    assert "Display-only face groups" in measure_response.json()["detail"]


def test_hardware_validation_reports_checks() -> None:
    with TestClient(app) as client:
        page = client.get("/hardware")
        response = client.get("/api/hardware/validation")
    assert page.status_code == 200
    payload = response.json()
    assert payload["total"] >= 8
    assert any(item["id"] == "privacy" and item["passed"] for item in payload["checks"])
    assert any(item["id"] == "body_fps" and "≥ 8 FPS" in item["label"] for item in payload["checks"])
    assert len(payload["requires_physical_validation"]) >= 4


def test_performance_health_endpoint_explains_traffic_light() -> None:
    with TestClient(app) as client:
        response = client.get("/api/performance/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["overall"] in {"green", "yellow", "red"}
    assert payload["face"]["level"] in {"green", "yellow", "red"}
    assert payload["body"]["reason"]


def test_phase14_session_exports_and_database_backup() -> None:
    participant = repository.create_participant("EXPORT_TEST", "Export Test", "test")
    with TestClient(app) as client:
        started = client.post("/api/sessions/start", json={"participant_id": participant.id}).json()
        client.post(f"/api/sessions/{started['id']}/stop", json={})
        json_export = client.get(f"/api/exports/sessions/{started['id']}.json")
        report_page = client.get(f"/reports/{started['id']}")
        zip_export = client.get(f"/api/exports/sessions/{started['id']}.zip")
        backup = client.get("/api/exports/database-backup.zip")
    assert json_export.status_code == 200
    assert json_export.json()["schema_version"] == "2.0"
    assert json_export.json()["session"]["participant_code"] == "EXPORT_TEST"
    assert json_export.json()["participant"]["code"] == "EXPORT_TEST"
    assert json_export.json()["interpretation"]["type"] == "descriptive_research_summary"
    assert json_export.json()["research_screening"]["clinically_validated"] is False
    assert json_export.json()["research_screening"]["status"] == "descriptive_only"
    assert json_export.json()["research_screening"]["score"] is None
    assert json_export.json()["research_features"]
    assert len(json_export.json()["research_basis"]) == 3
    assert "Behavioral Session Records" in report_page.text
    assert "Research screening summary" not in report_page.text
    assert "No-ADHD" not in report_page.text
    assert "Trial-by-trial records" in report_page.text
    assert zip_export.status_code == 200 and zip_export.content.startswith(b"PK")
    assert backup.status_code == 200 and backup.content.startswith(b"PK")
    with TestClient(app) as client:
        events = client.get("/api/audit").json()
    assert any(item["action"] == "export.database_backup" for item in events)


def test_phase15_signed_session_token_rejects_tampering() -> None:
    token = issue_token()
    assert valid_token(token)
    assert not valid_token(token + "changed")


def test_compact_dashboard_and_safe_record_deletion() -> None:
    participant = repository.create_participant("DELETE_TEST", None, None)
    with TestClient(app) as client:
        page = client.get("/")
        assert "Research session overview" in page.text and "Manage participants" in page.text
        assert 'id="theme-toggle"' in page.text and 'class="icon-button sidebar-toggle"' in page.text
        assert "System tools" in page.text and "Configuration and maintenance" in page.text
        started = client.post("/api/sessions/start", json={"participant_id": participant.id}).json()
        blocked = client.delete(f"/api/sessions/{started['id']}?confirm=true")
        assert blocked.status_code == 409
        client.post(f"/api/sessions/{started['id']}/stop", json={})
        assert client.delete(f"/api/sessions/{started['id']}").status_code == 400
        assert client.delete(f"/api/sessions/{started['id']}?confirm=true").status_code == 204
        assert client.delete(f"/api/participants/{participant.id}?confirm=true").status_code == 204


def test_attention_task_professional_workflow_page() -> None:
    with TestClient(app) as client:
        page = client.get("/attention-task")
        status = client.get("/api/attention/status")
        display_info = client.get("/api/participant-display/info")
        display_qr = client.get(display_info.json()["qr_url"])
        paired_url = display_info.json()["url"]
        display_token = paired_url.split("token=", 1)[1]
        public_status = client.get(f"/api/participant-task/status?token={display_token}")
        rejected = client.get("/api/participant-task/status?token=invalid-token-that-is-long-enough")
    assert page.status_code == 200
    assert "Start / repeat practice" in page.text
    assert "Begin recorded game" in page.text
    assert 'id="connection-screen"' in page.text
    assert 'id="waiting-screen"' in page.text
    assert "Participant experience" in client.get("/static/css/attention-task.css").text
    assert status.status_code == 200
    assert "trial_number" in status.json()
    assert display_info.status_code == 200 and "/attention-task?token=" in paired_url
    assert display_qr.status_code == 200 and "image/svg+xml" in display_qr.headers["content-type"]
    assert public_status.status_code == 200 and public_status.json()["phase"] == "waiting"
    assert rejected.status_code == 401


def test_age_adapted_attention_catalog_and_saved_configuration() -> None:
    participant = repository.create_participant("TASK_CONFIG", "Task Test", "Grade 9")
    with TestClient(app) as client:
        catalog = client.get("/api/attention/catalog")
        assert catalog.status_code == 200
        assert set(catalog.json()["tasks"]) == {"pop_balloon"}
        assert catalog.json()["goal_presets"] == [10, 15, 20, 30]
        assert {"child", "preteen", "teen", "adult"} == set(catalog.json()["age_profiles"])

        started_session = client.post("/api/sessions/start", json={"participant_id": participant.id})
        assert started_session.status_code == 201
        session_id = started_session.json()["id"]
        assert client.get("/api/participant-display/info").status_code == 200
        started_task = client.post("/api/attention/start", json={
            "task_key": "pop_balloon", "age_profile": "teen", "difficulty": "standard",
            "required_pops": 30, "game_mode": "target_color", "target_color": "purple",
        })
        assert started_task.status_code == 200
        assert started_task.json()["task_key"] == "pop_balloon"
        assert started_task.json()["age_profile"] == "teen"
        assert started_task.json()["difficulty"] == "standard"
        duplicate = client.post("/api/attention/start", json={
            "task_key": "pop_balloon", "age_profile": "child", "difficulty": "easy",
            "required_pops": 15, "game_mode": "any",
        })
        assert duplicate.status_code == 409
        client.post("/api/attention/abort")
        client.post(f"/api/sessions/{session_id}/stop", json={})
        exported = client.get(f"/api/exports/sessions/{session_id}.json")

    configurations = exported.json()["attention_configuration"]
    assert configurations[-1]["task_key"] == "pop_balloon"
    assert configurations[-1]["age_profile"] == "teen"
    assert configurations[-1]["difficulty"] == "standard"


def test_secure_tablet_pairing_practice_and_recorded_trial_end_to_end() -> None:
    participant = repository.create_participant("PAIR_FLOW", "Paired Participant", "8 years")
    with TestClient(app) as client:
        session = client.post("/api/sessions/start", json={"participant_id": participant.id}).json()
        first = client.get("/api/participant-display/info").json()
        old_token = first["url"].split("token=", 1)[1]
        second = client.get("/api/participant-display/info").json()
        token = second["url"].split("token=", 1)[1]
        assert client.get(f"/api/participant-task/status?token={old_token}").status_code == 401

        practice = client.post("/api/attention/practice", json={
            "task_key": "pop_balloon", "age_profile": "child", "difficulty": "easy",
            "required_pops": 5, "game_mode": "any"})
        assert practice.status_code == 200 and practice.json()["phase"] == "practice"
        assert client.post(f"/api/participant-task/practice-complete?token={token}").json()["phase"] == "ready"

        started = client.post("/api/attention/start", json={
            "task_key": "pop_balloon", "age_profile": "child", "difficulty": "easy",
            "required_pops": 5, "game_mode": "any"})
        assert started.status_code == 200
        trial = client.post(f"/api/participant-task/trials/next?token={token}").json()
        assert trial["stimulus_data"]["color"] in {"coral", "sky", "turquoise", "yellow", "purple", "orange", "green", "pink"}
        recovered = client.post(f"/api/participant-task/recover?token={token}")
        assert recovered.status_code == 200 and recovered.json()["trial_number"] == 0
        retried = client.post(f"/api/participant-task/trials/next?token={token}").json()
        assert retried["trial_number"] == 1
        completed = client.post(
            f"/api/participant-task/trials/{retried['id']}/complete?token={token}",
            json={"responded": True, "reaction_time_ms": 250})
        assert completed.status_code == 200
        client.post("/api/attention/abort")
        client.post(f"/api/sessions/{session['id']}/stop", json={})
