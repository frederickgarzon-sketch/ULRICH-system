"""Isolated SQLite tests; no server, AI models, cameras or real records."""
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from app.database.database import Base
from app.database.models import MonitoringSession, Participant, ShapeMatchingRun
from app.tasks import shape_matching as service


@pytest.fixture
def setup(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'shape.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(service, "SessionLocal", factory)
    with factory() as db:
        p = Participant(participant_code="SYNTHETIC_SHAPE")
        db.add(p); db.flush()
        s = MonitoringSession(participant_id=p.id, mode="mock", status="active")
        db.add(s); db.commit(); sid = s.id
    yield sid, factory
    engine.dispose()


def row(status, n=1, outcome="matched", wrong=0, elapsed=100):
    return {"trial": n, "shape": status["plan"][n-1], "outcome": outcome,
            "wrong_drops": wrong, "active_ms": elapsed,
            "first_attempt_correct": outcome == "matched" and wrong == 0}


def test_plan_persisted_and_five_trials_complete_without_duplicates(setup):
    sid, factory = setup
    run = service.create_run(sid, 5); token = run["token"]
    assert "token_hash" not in run
    service.operate(token, "start")
    first = row(run)
    service.operate(token, "trial", first)
    assert len(service.operate(token, "trial", first)["rows"]) == 1
    for n in range(2, 6): result = service.operate(token, "trial", row(run, n))
    assert result["status"] == "complete"
    assert result["summary"]["matched"] == 5
    assert result["summary"]["first_attempt_accuracy_pct"] == 100
    assert service.operate(token)["plan"] == run["plan"]
    with factory() as db:
        assert db.scalar(select(ShapeMatchingRun)).rows_json


def test_token_session_and_run_boundaries(setup):
    sid, factory = setup
    run = service.create_run(sid, 5)
    with pytest.raises(ValueError): service.create_run(sid, 5)
    with pytest.raises(PermissionError): service.operate("invalid")
    with factory() as db:
        db.get(MonitoringSession, sid).status = "completed"; db.commit()
    with pytest.raises(PermissionError): service.operate(run["token"], "start")


def test_out_of_order_wrong_shape_and_conflicting_retry_rejected(setup):
    sid, _ = setup
    run = service.create_run(sid, 5); token = run["token"]
    service.operate(token, "start")
    with pytest.raises(ValueError): service.operate(token, "trial", row(run, 2))
    bad = {**row(run), "shape": "not-the-shape"}
    with pytest.raises(ValueError): service.operate(token, "trial", bad)
    service.operate(token, "trial", row(run))
    with pytest.raises(ValueError): service.operate(token, "trial", {**row(run), "active_ms": 200})


def test_pause_stop_and_reconnect_preserve_saved_attempts(setup):
    sid, _ = setup
    run = service.create_run(sid, 5); token = run["token"]
    service.operate(token, "start")
    service.operate(token, "trial", row(run))
    service.operate(token, "pause")
    assert service.operate(token)["status"] == "paused"
    with pytest.raises(ValueError): service.operate(token, "trial", row(run, 2))
    result = service.operate(token, "trial", row(run, 2, "stopped"))
    assert result["status"] == "stopped"
    assert result["summary"]["saved_trials"] == 2
    assert result["summary"]["unfinished_trials"] == 3


@pytest.mark.parametrize("outcome,wrong,elapsed", [("timeout",0,1),("assistance_limit",1,50),("matched",4,50)])
def test_invalid_outcomes_do_not_save(setup, outcome, wrong, elapsed):
    sid, _ = setup
    run = service.create_run(sid, 5)
    service.operate(run["token"], "start")
    with pytest.raises(ValueError): service.operate(run["token"], "trial", row(run, outcome=outcome, wrong=wrong, elapsed=elapsed))
    assert service.operate(run["token"])["rows"] == []


def test_separate_report_json_csv_and_session_delete(setup, monkeypatch):
    import importlib, io, json, zipfile
    repository_module = importlib.import_module("app.database.repository")
    exports = importlib.import_module("app.services.export_service")
    sid, factory = setup
    monkeypatch.setattr(repository_module, "SessionLocal", factory)
    run = service.create_run(sid, 5)
    service.operate(run["token"], "start")
    service.operate(run["token"], "trial", row(run))
    report = repository_module.repository.build_report(sid)
    assert report["shape_matching"][0]["summary"]["matched"] == 1
    assert report["attention"]["trials"] == []
    assert "token_hash" not in json.dumps(report)
    exported = json.loads(exports.session_json(sid))
    assert exported["schema_version"] == "2.1"
    with zipfile.ZipFile(io.BytesIO(exports.session_archive(sid))) as archive:
        csv_text = archive.read("shape_matching_trials.csv").decode("utf-8-sig")
        assert "shape_matching" in csv_text and "matched" in csv_text
    with factory() as db:
        db.get(MonitoringSession, sid).status = "completed"; db.commit()
    assert repository_module.repository.build_report(sid)["shape_matching"][0]["status"] == "interrupted"
    repository_module.repository.delete_session(sid)
    with factory() as db: assert db.scalar(select(ShapeMatchingRun)) is None


def test_operator_stop_releases_abandoned_pairing(setup):
    sid, _ = setup
    service.create_run(sid, 5)
    assert service.active_run(sid)
    assert service.stop_active(sid)["stopped_runs"] == 1
    assert not service.active_run(sid)
    assert service.create_run(sid, 5)["status"] == "waiting"


def test_expired_pairing_cannot_read_or_write(setup):
    from datetime import datetime, timezone, timedelta
    sid, factory = setup
    run = service.create_run(sid, 5)
    with factory() as db:
        db.get(ShapeMatchingRun, run["id"]).created_at = datetime.now(timezone.utc)-timedelta(hours=9)
        db.commit()
    with pytest.raises(PermissionError): service.operate(run["token"])


def test_completed_trial_retry_does_not_repeat_task_phase_transition(setup):
    sid, _ = setup
    run = service.create_run(sid, 5); token = run["token"]
    assert service.operate(token, "start")["_status_changed"]
    assert not service.operate(token, "start")["_status_changed"]
    for n in range(1, 6): result = service.operate(token, "trial", row(run, n))
    assert result["_status_changed"]
    assert not service.operate(token, "trial", row(run, 5))["_status_changed"]
