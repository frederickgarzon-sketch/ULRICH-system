"""Durable token-scoped Shape Matching runs. Client timings are descriptive."""
import hashlib
import json
import secrets
import threading
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from app.database.database import SessionLocal
from app.database.models import MonitoringSession, ShapeMatchingRun

SHAPES = ("circle", "square", "triangle", "star")
_lock = threading.RLock()


def summary(rows, planned):
    matched = [r for r in rows if r["outcome"] == "matched"]
    return {"planned_trials": planned, "saved_trials": len(rows), "matched": len(matched),
            "unfinished_trials": max(0, planned-len(rows)),
            "wrong_drops": sum(r["wrong_drops"] for r in rows),
            "first_attempt_accuracy_pct": round(sum(r["first_attempt_correct"] for r in rows)*100/len(rows), 1) if rows else None,
            "active_ms": sum(r["active_ms"] for r in rows)}


def payload(run):
    plan, rows = json.loads(run.plan_json), json.loads(run.rows_json)
    return {"id": run.id, "session_id": run.session_id, "game_type": "shape_matching",
            "created_at": run.created_at.isoformat(),
            "version": "shape-1.0", "status": run.status, "plan": plan,
            "rows": rows, "summary": summary(rows, len(plan)),
            "timing_source": "browser_active_time_unvalidated"}


def create_run(session_id, count):
    if type(count) is not int or not 5 <= count <= 50:
        raise ValueError("Choose 5–50 trials")
    token = secrets.token_urlsafe(32)
    plan = [SHAPES[i % 4] for i in range(count)]
    secrets.SystemRandom().shuffle(plan)
    with _lock, SessionLocal() as db:
        session = db.get(MonitoringSession, session_id)
        if session is None or session.status != "active":
            raise ValueError("Start an active participant session first")
        if db.scalar(select(ShapeMatchingRun).where(ShapeMatchingRun.session_id == session_id,
                     ShapeMatchingRun.status.in_(["waiting", "recording", "paused"]))):
            raise ValueError("Finish or stop the current Shape Matching run first")
        run = ShapeMatchingRun(session_id=session_id, token_hash=hashlib.sha256(token.encode()).hexdigest(),
                               plan_json=json.dumps(plan), rows_json="[]", status="waiting")
        db.add(run); db.commit()
        return {**payload(run), "token": token}


def active_run(session_id):
    if session_id is None: return False
    with SessionLocal() as db:
        return db.scalar(select(ShapeMatchingRun.id).where(ShapeMatchingRun.session_id == session_id,
                         ShapeMatchingRun.status.in_(["waiting", "recording", "paused"]))) is not None


def stop_active(session_id):
    with _lock, SessionLocal() as db:
        runs = list(db.scalars(select(ShapeMatchingRun).where(ShapeMatchingRun.session_id == session_id,
                         ShapeMatchingRun.status.in_(["waiting", "recording", "paused"]))))
        for run in runs: run.status = "stopped"
        db.commit()
        return {"stopped_runs": len(runs)}


def operate(token, action="status", row=None):
    with _lock, SessionLocal() as db:
        run = db.scalar(select(ShapeMatchingRun).where(ShapeMatchingRun.token_hash == hashlib.sha256(token.encode()).hexdigest()))
        if run is None:
            raise PermissionError("Invalid Shape Matching pairing")
        created = run.created_at.replace(tzinfo=timezone.utc) if run.created_at.tzinfo is None else run.created_at
        if datetime.now(timezone.utc)-created > timedelta(hours=8):
            raise PermissionError("Shape Matching pairing expired")
        session = db.get(MonitoringSession, run.session_id)
        if session is None or session.status != "active":
            raise PermissionError("The linked monitoring session has ended")
        rows, plan = json.loads(run.rows_json), json.loads(run.plan_json)
        previous_status = run.status
        if action == "start":
            if run.status == "waiting": run.status = "recording"
            elif run.status not in {"recording", "paused"}: raise ValueError("Run already ended")
        elif action == "pause" and run.status == "recording": run.status = "paused"
        elif action == "resume" and run.status == "paused": run.status = "recording"
        elif action == "stop" and run.status in {"waiting", "recording", "paused"}: run.status = "stopped"
        elif action == "trial":
            n = row["trial"]
            if n <= len(rows):
                if rows[n-1] != row: raise ValueError("Conflicting duplicate trial")
                return {**payload(run), "_status_changed": False}  # No repeated phase transition.
            if (run.status != "recording" and not (run.status == "paused" and row["outcome"] == "stopped")) or n != len(rows)+1 or n > len(plan):
                raise ValueError("Trial is out of order or run is not recording")
            if row["shape"] != plan[n-1]: raise ValueError("Shape differs from saved plan")
            if row["outcome"] not in {"matched", "timeout", "assistance_limit", "stopped"}: raise ValueError("Invalid outcome")
            wrong, elapsed = row["wrong_drops"], row["active_ms"]
            if not 0 <= wrong <= 3 or not 0 <= elapsed <= 31000: raise ValueError("Invalid attempt measurements")
            expected = row["outcome"] == "matched" and wrong == 0
            if row["first_attempt_correct"] != expected: raise ValueError("Incorrect first-attempt flag")
            if row["outcome"] == "assistance_limit" and wrong != 3: raise ValueError("Assistance limit requires three errors")
            if row["outcome"] == "matched" and wrong >= 3: raise ValueError("Three errors ends an attempt before a match")
            if row["outcome"] == "timeout" and elapsed < 30000: raise ValueError("Timeout is premature")
            rows.append(row); run.rows_json = json.dumps(rows)
            if row["outcome"] == "stopped": run.status = "stopped"
            elif len(rows) == len(plan): run.status = "complete"
        elif action not in {"status", "start", "pause", "resume", "stop"}: raise ValueError("Unknown action")
        db.commit()
        return {**payload(run), "_status_changed": run.status != previous_status}
