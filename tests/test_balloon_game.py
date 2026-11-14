"""Focused contract tests for the Pop the Balloon participant activity."""

from __future__ import annotations

import csv
import io
import json
import time
import zipfile
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database.database import SessionLocal
from app.database.models import AttentionTaskRun
from app.main import app
from app.tasks.attention_task import BALLOON_COLORS, AttentionTaskService, attention_task_service


def setup_game(client: TestClient, *, difficulty: str = "easy", mode: str = "any",
               goal: int = 5, color: str = "sky") -> tuple[int, str]:
    participant = client.post("/api/participants", json={
        "participant_code": "BALLOON_" + uuid4().hex[:10], "age_group": "Child"
    }).json()
    session = client.post("/api/sessions/start", json={"participant_id": participant["id"]}).json()
    pairing = client.get("/api/participant-display/info").json()
    token = parse_qs(urlparse(pairing["url"]).query)["token"][0]
    assert client.get("/api/participant-task/status", params={"token": token}).status_code == 200
    config = {"task_key": "pop_balloon", "age_profile": "child", "difficulty": difficulty,
              "required_pops": goal, "game_mode": mode, "target_color": color,
              "maximum_duration_seconds": 300}
    practice = client.post("/api/attention/practice", json=config).json()
    assert len(practice["practice_stimuli"]) == 5
    client.post("/api/participant-task/practice-complete", params={
        "token": token, "generation": practice["practice_generation"]}).raise_for_status()
    client.post("/api/attention/start", json=config).raise_for_status()
    return session["id"], token


def complete_next(client: TestClient, token: str, *, respond_to_target: bool = True,
                  respond_to_distractor: bool = False):
    trial = client.post("/api/participant-task/trials/next", params={"token": token}).json()
    responded = respond_to_target if trial["is_target"] else respond_to_distractor
    response = client.post(f"/api/participant-task/trials/{trial['id']}/complete",
        params={"token": token}, json={"responded": responded,
        "reaction_time_ms": 240 if responded else None, "premature_taps": 1})
    response.raise_for_status()
    return trial, response.json()


@pytest.mark.parametrize("color", list(BALLOON_COLORS))
def test_each_target_color_advances_tap_and_timeout_and_reconciles(color):
    with TestClient(app) as client:
        session_id, token = setup_game(client, difficulty="moderate", mode="target_color", color=color)
        seen = set()
        for index in range(15):
            trial = client.post("/api/participant-task/trials/next", params={"token": token}).json()
            assert trial["trial_number"] == index + 1
            seen.add(trial["stimulus_data"]["color"])
            # A missed target (timeout) must also advance; later target taps count.
            responded = trial["is_target"] and index > 0
            result = client.post(f"/api/participant-task/trials/{trial['id']}/complete",
                params={"token": token}, json={"responded": responded,
                "reaction_time_ms": trial["display_ms"] if responded else None})
            result.raise_for_status()
            saved = client.get(f"/api/participant-task/trials/{trial['id']}/status", params={"token": token})
            assert saved.status_code == 200 and saved.json()["completed"] is True
            if result.json()["phase"] == "complete": break
        assert color in seen
        assert client.get("/api/participant-task/trials/999999/status", params={"token":token}).status_code == 409
        client.post("/api/attention/abort"); client.post(f"/api/sessions/{session_id}/stop")


@pytest.mark.parametrize("difficulty,mode,size,speed", [
    ("easy", "any", 176, "slow"),
    ("moderate", "target_color", 148, "normal"),
    ("hard", "target_color", 120, "fast"),
])
def test_difficulty_presentation_contract(difficulty, mode, size, speed):
    service = AttentionTaskService()
    plan = service._build_stimulus_plan(15, 5, difficulty, mode, "sky",
                                        __import__("random").Random(14), practice=False)
    assert all(item["speed"] == speed for item in plan)
    assert all(round(size * .92) <= item["size_px"] <= round(size * 1.08) for item in plan)
    assert all(item["color"] in BALLOON_COLORS for item in plan)
    if mode == "any": assert all(item["is_target"] for item in plan)
    else: assert any(not item["is_target"] for item in plan)


def test_custom_goal_boundaries_and_easy_mode_gate():
    with TestClient(app) as client:
        participant = client.post("/api/participants", json={"participant_code":"LIMIT_"+uuid4().hex[:8]}).json()
        session = client.post("/api/sessions/start", json={"participant_id":participant["id"]}).json()
        client.get("/api/participant-display/info")
        assert client.post("/api/attention/start", json={"required_pops":4}).status_code == 422
        assert client.post("/api/attention/start", json={"required_pops":51}).status_code == 422
        assert client.post("/api/attention/start", json={"required_pops":5,"difficulty":"easy","game_mode":"target_color"}).status_code == 409
        assert client.post("/api/attention/start", json={"required_pops":50,"difficulty":"easy","game_mode":"any"}).status_code == 200
        client.post("/api/attention/abort"); client.post(f"/api/sessions/{session['id']}/stop")


def test_goal_completion_duplicate_tap_and_practice_exclusion():
    with TestClient(app) as client:
        session_id, token = setup_game(client, goal=5)
        last_trial = None
        for _ in range(5): last_trial, result = complete_next(client, token)
        assert result["phase"] == "complete" and result["correct_pops"] == 5
        duplicate = client.post(f"/api/participant-task/trials/{last_trial['id']}/complete",
            params={"token":token}, json={"responded":True,"reaction_time_ms":240})
        assert duplicate.status_code == 409
        report = client.get(f"/api/reports/{session_id}").json()
        assert report["attention"]["total_attempts"] == 5
        assert report["attention"]["premature_taps"] == 5
        assert all(item["phase"] == "recorded" for item in report["attention"]["trials"])
        client.post(f"/api/sessions/{session_id}/stop")


def test_target_color_miss_and_false_response_are_separate():
    with TestClient(app) as client:
        session_id, token = setup_game(client, difficulty="hard", mode="target_color", goal=5, color="purple")
        saw_target = saw_distractor = False
        for _ in range(15):
            trial, _ = complete_next(client, token, respond_to_target=False, respond_to_distractor=True)
            saw_target |= trial["is_target"]; saw_distractor |= not trial["is_target"]
        summary = client.get(f"/api/attention/sessions/{session_id}/summary").json()
        assert saw_target and saw_distractor and summary["missed"] > 0 and summary["incorrect_pops"] > 0
        client.post("/api/attention/abort"); client.post(f"/api/sessions/{session_id}/stop")


def test_pause_discards_unfinished_balloon_and_replays_same_plan_item():
    with TestClient(app) as client:
        session_id, token = setup_game(client, goal=5)
        first = client.post("/api/participant-task/trials/next", params={"token":token}).json()
        assert client.post("/api/attention/pause").json()["phase"] == "paused"
        assert client.post("/api/attention/resume").json()["phase"] == "recording"
        replay = client.post("/api/participant-task/trials/next", params={"token":token}).json()
        assert replay["trial_number"] == first["trial_number"]
        assert replay["stimulus_data"]["code"] == first["stimulus_data"]["code"]
        client.post("/api/attention/abort"); client.post(f"/api/sessions/{session_id}/stop")


def test_disconnect_auto_pause_and_reconnect_restore(monkeypatch):
    service = AttentionTaskService(); monkeypatch.setattr("app.tasks.attention_task.session_manager._active_id", 991)
    token = service.pair_display()["token"]; service.validate_display_token(token)
    service._run_id = 45; service._display_phase = "recording"
    service._last_display_seen = time.monotonic() - 9
    paused = service.public_status()
    assert paused["phase"] == "paused" and paused["pause_reason"] == "connection_lost"
    service.validate_display_token(token)
    restored = service.public_status()
    assert restored["phase"] == "recording" and restored["pause_reason"] is None


def test_browser_recovery_reuses_exact_stimulus():
    with TestClient(app) as client:
        session_id, token = setup_game(client, goal=5)
        first = client.post("/api/participant-task/trials/next", params={"token":token}).json()
        client.post("/api/participant-task/recover", params={"token":token}).raise_for_status()
        replay = client.post("/api/participant-task/trials/next", params={"token":token}).json()
        assert replay["trial_number"] == 1 and replay["stimulus_data"] == first["stimulus_data"]
        client.post("/api/attention/abort"); client.post(f"/api/sessions/{session_id}/stop")


def test_practice_can_be_cancelled_and_repeated_without_recording_trials():
    with TestClient(app) as client:
        participant = client.post("/api/participants", json={
            "participant_code": "PRACTICE_" + uuid4().hex[:8], "age_group": "Child"
        }).json()
        session = client.post("/api/sessions/start", json={"participant_id": participant["id"]}).json()
        pairing = client.get("/api/participant-display/info").json()
        token = parse_qs(urlparse(pairing["url"]).query)["token"][0]
        client.get("/api/participant-task/status", params={"token": token}).raise_for_status()
        config = {"task_key": "pop_balloon", "age_profile": "child", "difficulty": "easy",
                  "required_pops": 5, "game_mode": "any", "target_color": "sky"}
        first = client.post("/api/attention/practice", json=config).json()
        cancelled = client.post("/api/attention/practice/cancel", params={
            "generation": first["practice_generation"]})
        assert cancelled.status_code == 200 and cancelled.json()["phase"] == "waiting"
        repeated = client.post("/api/attention/practice", json=config).json()
        assert repeated["phase"] == "practice"
        assert repeated["practice_generation"] > first["practice_generation"]
        helped = client.post("/api/participant-task/practice-help", params={
            "token": token, "generation": repeated["practice_generation"]})
        assert helped.status_code == 200 and helped.json()["phase"] == "waiting"
        assert "3 tries" in helped.json()["practice_notice"]
        assert "3 tries" in client.get("/api/participant-task/status", params={"token":token}).json()["practice_notice"]
        assert not client.post("/api/attention/practice", json=config).json()["practice_notice"]
        assert client.get(f"/api/attention/sessions/{session['id']}/summary").json()["total_attempts"] == 0
        client.post(f"/api/sessions/{session['id']}/stop")


def test_early_end_reason_is_saved_and_session_stop_aborts_an_active_game():
    with TestClient(app) as client:
        session_id, token = setup_game(client, goal=5)
        complete_next(client, token)
        ended = client.post("/api/attention/abort", json={"reason": "participant_requested_stop"})
        assert ended.status_code == 200 and ended.json()["reason"] == "participant_requested_stop"
        with SessionLocal() as db:
            run = db.scalar(__import__("sqlalchemy").select(AttentionTaskRun).where(
                AttentionTaskRun.session_id == session_id).order_by(AttentionTaskRun.id.desc()))
            assert run.status == "aborted" and run.termination_reason == "participant_requested_stop"
        # A new task can be started and is safely closed when monitoring stops.
        pairing = client.get("/api/participant-display/info").json()
        new_token = parse_qs(urlparse(pairing["url"]).query)["token"][0]
        client.get("/api/participant-task/status", params={"token": new_token}).raise_for_status()
        config = {"task_key": "pop_balloon", "age_profile": "child", "difficulty": "easy",
                  "required_pops": 5, "game_mode": "any", "target_color": "sky"}
        practice = client.post("/api/attention/practice", json=config).json()
        client.post("/api/participant-task/practice-complete", params={
            "token": new_token, "generation": practice["practice_generation"]}).raise_for_status()
        client.post("/api/attention/start", json=config).raise_for_status()
        assert client.post(f"/api/sessions/{session_id}/stop").status_code == 200
        with SessionLocal() as db:
            latest = db.scalar(__import__("sqlalchemy").select(AttentionTaskRun).where(
                AttentionTaskRun.session_id == session_id).order_by(AttentionTaskRun.id.desc()))
            assert latest.status == "aborted" and latest.termination_reason == "operator_ended"


def test_balloon_json_csv_and_database_backup_exports():
    with TestClient(app) as client:
        session_id, token = setup_game(client, goal=5)
        complete_next(client, token)
        exported = client.get(f"/api/exports/sessions/{session_id}.json").json()
        config = exported["attention_configuration"][-1]["configuration"]
        assert config["random_seed"] and len(config["stimulus_sequence"]) == 15
        assert config["required_correct_pops"] == 5
        archive = zipfile.ZipFile(io.BytesIO(client.get(f"/api/exports/sessions/{session_id}.zip").content))
        rows = list(csv.DictReader(io.TextIOWrapper(archive.open("attention_trials.csv"), encoding="utf-8-sig")))
        assert rows and rows[0]["balloon_color"] and rows[0]["x_percent"]
        backup = client.get("/api/exports/database-backup.zip")
        assert backup.status_code == 200 and backup.content.startswith(b"PK")
        client.post("/api/attention/abort"); client.post(f"/api/sessions/{session_id}/stop")


def test_historical_task_record_remains_readable():
    with TestClient(app) as client:
        participant = client.post("/api/participants", json={"participant_code":"LEGACY_"+uuid4().hex[:8]}).json()
        session = client.post("/api/sessions/start", json={"participant_id":participant["id"]}).json()
        with SessionLocal() as db:
            db.add(AttentionTaskRun(session_id=session["id"], participant_id=participant["id"],
                task_key="go_no_go", task_version="1.0", age_profile="child", difficulty="easy",
                configuration_json=json.dumps({"legacy":True}), status="completed")); db.commit()
        report = client.get(f"/api/reports/{session['id']}").json()
        assert report["attention_configuration"][-1]["task_key"] == "go_no_go"
        assert report["attention_configuration"][-1]["configuration"] == {"legacy":True}
        client.post(f"/api/sessions/{session['id']}/stop")
