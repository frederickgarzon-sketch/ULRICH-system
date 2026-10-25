"""Versioned research protocols with explicit capability and validity gates."""

from __future__ import annotations

import json
import random
import secrets
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from sqlalchemy import select

from app.database.database import SessionLocal
from app.database.models import ResearchTaskRun, ResearchTaskTrial
from app.sessions.session_manager import session_manager


@dataclass(frozen=True, slots=True)
class ProtocolDefinition:
    key: str
    version: str
    name: str
    description: str
    estimated_minutes: int
    requires_validated_gaze: bool
    implementation_status: str
    non_diagnostic: bool = True


PROTOCOLS = {
    "eye_control_standard": ProtocolDefinition(
        key="eye_control_standard",
        version="1.0.0-draft",
        name="Eye Control Standard",
        description="30-second fixation plus balanced prosaccade and antisaccade trials.",
        estimated_minutes=6,
        requires_validated_gaze=True,
        implementation_status="validation_required",
    ),
    "everyday_planning_pilot": ProtocolDefinition(
        key="everyday_planning_pilot",
        version="0.1.0-draft",
        name="Everyday Planning Pilot",
        description="Locally adapted multi-step task; not an EPELI implementation.",
        estimated_minutes=10,
        requires_validated_gaze=False,
        implementation_status="planned",
    ),
}


class ResearchTaskConflict(RuntimeError):
    pass


def protocol_catalog() -> list[dict[str, object]]:
    return [asdict(item) for item in PROTOCOLS.values()]


def build_eye_control_plan(seed: int) -> list[dict[str, object]]:
    """Return a reproducible, balanced plan; practice is never scored as recorded data."""
    rng = random.Random(seed)
    plan: list[dict[str, object]] = [
        {"phase": "recorded", "task_type": "fixation", "cue": "FIXATE",
         "target_direction": None, "expected_direction": "center", "requires_gaze": True}
    ]
    practice = []
    for task_type in ("prosaccade", "antisaccade"):
        for direction in ("left", "right"):
            expected = direction if task_type == "prosaccade" else ("right" if direction == "left" else "left")
            practice.append({"phase": "practice", "task_type": task_type,
                             "cue": task_type.upper(), "target_direction": direction,
                             "expected_direction": expected, "requires_gaze": True})
    rng.shuffle(practice)
    recorded = []
    for task_type in ("prosaccade", "antisaccade"):
        for direction in ("left", "right"):
            expected = direction if task_type == "prosaccade" else ("right" if direction == "left" else "left")
            for _ in range(7):
                recorded.append({"phase": "recorded", "task_type": task_type,
                                 "cue": task_type.upper(), "target_direction": direction,
                                 "expected_direction": expected, "requires_gaze": True})
    rng.shuffle(recorded)
    return practice + plan + recorded


class ResearchTaskService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._run_id: int | None = None
        self._active_trial_id: int | None = None

    def start(self, protocol_key: str, *, seed: int | None = None,
              gaze_provider: str = "unavailable", gaze_validated: bool = False) -> dict[str, object]:
        session_id = session_manager.active_session_id
        if session_id is None:
            raise ResearchTaskConflict("Start a monitoring session before a research task")
        protocol = PROTOCOLS.get(protocol_key)
        if protocol is None:
            raise ResearchTaskConflict("Unknown research protocol")
        if protocol.implementation_status == "planned":
            raise ResearchTaskConflict("This protocol is documented but not implemented yet")
        if protocol.requires_validated_gaze and not gaze_validated:
            raise ResearchTaskConflict("Validated gaze provider required; eye landmarks are not gaze tracking")
        actual_seed = seed if seed is not None else secrets.randbelow(2_147_483_647)
        plan = build_eye_control_plan(actual_seed)
        configuration = {"protocol": asdict(protocol), "trial_count": len(plan),
                         "recorded_fixation_seconds": 30, "center_gate_ms": 500}
        with self._lock, SessionLocal() as db:
            run = ResearchTaskRun(
                session_id=session_id, protocol_key=protocol.key, protocol_version=protocol.version,
                random_seed=actual_seed, configuration_json=json.dumps(configuration, sort_keys=True),
                gaze_provider=gaze_provider, gaze_validated=gaze_validated,
            )
            db.add(run)
            db.flush()
            for number, item in enumerate(plan, start=1):
                db.add(ResearchTaskTrial(run_id=run.id, session_id=session_id,
                                         sequence_number=number, **item))
            db.commit()
            db.refresh(run)
            self._run_id = run.id
            self._active_trial_id = None
        return self.status()

    def next_trial(self) -> dict[str, object]:
        with self._lock:
            run = self._require_active_run()
            if self._active_trial_id is not None:
                raise ResearchTaskConflict("Complete or invalidate the current trial first")
            with SessionLocal() as db:
                trial = db.scalar(select(ResearchTaskTrial).where(
                    ResearchTaskTrial.run_id == run.id,
                    ResearchTaskTrial.status == "planned",
                ).order_by(ResearchTaskTrial.sequence_number).limit(1))
                if trial is None:
                    run_db = db.get(ResearchTaskRun, run.id)
                    run_db.status = "complete"
                    run_db.completed_at = datetime.now(timezone.utc)
                    db.commit()
                    return {"complete": True, "run_id": run.id}
                trial.status = "active"
                trial.started_at = datetime.now(timezone.utc)
                db.commit()
                db.refresh(trial)
                self._active_trial_id = trial.id
                return self._trial_payload(trial)

    def complete_trial(self, trial_id: int, *, observed_direction: str | None,
                       response_latency_ms: float | None, client_started_ms: float | None,
                       client_completed_ms: float | None, tracking_valid: bool,
                       invalid_reason: str | None = None, metrics: dict[str, object] | None = None) -> dict[str, object]:
        with self._lock:
            run = self._require_active_run()
            if trial_id != self._active_trial_id:
                raise ResearchTaskConflict("Trial is not current or was already completed")
            with SessionLocal() as db:
                trial = db.get(ResearchTaskTrial, trial_id)
                if trial is None or trial.run_id != run.id:
                    raise ResearchTaskConflict("Trial not found for active run")
                valid = tracking_valid and (not trial.requires_gaze or run.gaze_validated)
                reason = invalid_reason
                if trial.requires_gaze and not run.gaze_validated:
                    valid, reason = False, "gaze_provider_not_validated"
                if not tracking_valid and not reason:
                    reason = "tracking_lost"
                trial.observed_direction = observed_direction
                trial.response_latency_ms = response_latency_ms
                trial.client_started_ms = client_started_ms
                trial.client_completed_ms = client_completed_ms
                trial.valid = valid
                trial.invalid_reason = None if valid else (reason or "invalid_trial")
                trial.correct = (observed_direction == trial.expected_direction) if valid else None
                trial.metrics_json = json.dumps(metrics or {}, sort_keys=True)
                trial.status = "complete" if valid else "invalid"
                trial.completed_at = datetime.now(timezone.utc)
                db.commit()
            self._active_trial_id = None
            return self.status()

    def abort(self) -> dict[str, object]:
        with self._lock:
            run_id = self._run_id
            if run_id is not None:
                with SessionLocal() as db:
                    run = db.get(ResearchTaskRun, run_id)
                    if run is not None and run.status == "active":
                        run.status = "aborted"
                        run.aborted_at = datetime.now(timezone.utc)
                        if self._active_trial_id is not None:
                            trial = db.get(ResearchTaskTrial, self._active_trial_id)
                            if trial is not None:
                                trial.status = "invalid"
                                trial.valid = False
                                trial.invalid_reason = "run_aborted"
                                trial.completed_at = datetime.now(timezone.utc)
                        db.commit()
            self._run_id = None
            self._active_trial_id = None
            return {"aborted": True, "run_id": run_id}

    def status(self) -> dict[str, object]:
        with self._lock:
            if self._run_id is None:
                return {"active": False, "run_id": None}
            with SessionLocal() as db:
                run = db.get(ResearchTaskRun, self._run_id)
                if run is None:
                    return {"active": False, "run_id": None}
                trials = list(db.scalars(select(ResearchTaskTrial).where(
                    ResearchTaskTrial.run_id == run.id).order_by(ResearchTaskTrial.sequence_number)))
                recorded = [item for item in trials if item.phase == "recorded"]
                valid = [item for item in recorded if item.valid]
                invalid = [item for item in recorded if item.status == "invalid"]
                return {
                    "active": run.status == "active", "run_id": run.id,
                    "session_id": run.session_id, "protocol_key": run.protocol_key,
                    "protocol_version": run.protocol_version, "status": run.status,
                    "random_seed": run.random_seed, "gaze_provider": run.gaze_provider,
                    "gaze_validated": run.gaze_validated, "active_trial_id": self._active_trial_id,
                    "total_trials": len(trials), "completed_trials": sum(t.status in {"complete", "invalid"} for t in trials),
                    "recorded_valid": len(valid), "recorded_invalid": len(invalid),
                }

    def _require_active_run(self) -> ResearchTaskRun:
        if self._run_id is None:
            raise ResearchTaskConflict("No active research task")
        with SessionLocal() as db:
            run = db.get(ResearchTaskRun, self._run_id)
            if run is None or run.status != "active":
                raise ResearchTaskConflict("No active research task")
            if run.session_id != session_manager.active_session_id:
                raise ResearchTaskConflict("Research task is not attached to the active session")
            db.expunge(run)
            return run

    @staticmethod
    def _trial_payload(trial: ResearchTaskTrial) -> dict[str, object]:
        return {
            "id": trial.id, "run_id": trial.run_id, "sequence_number": trial.sequence_number,
            "phase": trial.phase, "task_type": trial.task_type, "cue": trial.cue,
            "target_direction": trial.target_direction, "expected_direction": trial.expected_direction,
            "requires_gaze": trial.requires_gaze, "complete": False,
            "fixation_gate_ms": 500, "duration_ms": 30000 if trial.task_type == "fixation" else 1400,
        }


research_task_service = ResearchTaskService()
