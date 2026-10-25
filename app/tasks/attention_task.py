"""Configurable, non-diagnostic attention/reaction task."""

from __future__ import annotations

import random
import json
import secrets
import statistics
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import delete, select

from app.database.database import SessionLocal
from app.database.models import AttentionTrial, AttentionTaskRun, MonitoringSession, Participant
from app.sessions.session_manager import session_manager
from app.config import settings


@dataclass(frozen=True, slots=True)
class TrialScore:
    correct: bool
    incorrect: bool
    missed: bool
    false_response: bool


def score_trial(is_target: bool, responded: bool) -> TrialScore:
    correct = (is_target and responded) or (not is_target and not responded)
    missed = is_target and not responded
    false_response = not is_target and responded
    return TrialScore(correct, not correct, missed, false_response)


class AttentionTaskConflict(RuntimeError):
    pass


TASK_CATALOG = {
    "target_tap": {"name": "Target Tap", "description": "Respond to the target; ignore distractors.", "best_for": ["child", "preteen"], "instruction": "Tap only when you see the target."},
    "go_no_go": {"name": "Go / No-Go", "description": "Respond to GO and wait on STOP.", "best_for": ["child", "preteen", "teen", "adult"], "instruction": "Respond to GO. Do not respond to STOP."},
    "focus_match": {"name": "Focus Match", "description": "Respond when the two symbols match.", "best_for": ["preteen", "teen", "adult"], "instruction": "Respond when both symbols are the same."},
    "visual_search": {"name": "Visual Search", "description": "Find the different item among distractors.", "best_for": ["child", "preteen", "teen", "adult"], "instruction": "Respond when one item is different."},
    "pattern_memory": {"name": "Pattern Memory", "description": "Recognize the pattern shown before the trial.", "best_for": ["preteen", "teen", "adult"], "instruction": "Respond when the pattern matches."},
}
AGE_PROFILES = {
    "child": {"name": "Child", "ages": "6–9", "theme": "playful"},
    "preteen": {"name": "Pre-teen", "ages": "10–12", "theme": "friendly"},
    "teen": {"name": "Teen", "ages": "13–17", "theme": "neutral"},
    "adult": {"name": "Adult", "ages": "18+", "theme": "professional"},
}
DIFFICULTIES = {
    "easy": {"trials": 15, "display_ms": 1400, "intertrial_ms": 850, "target_probability": .40},
    "moderate": {"trials": 30, "display_ms": 1000, "intertrial_ms": 700, "target_probability": .30},
    "hard": {"trials": 45, "display_ms": 700, "intertrial_ms": 550, "target_probability": .25},
    "standard": {"trials": 30, "display_ms": 1000, "intertrial_ms": 700, "target_probability": .30},
}


def task_catalog() -> dict[str, object]:
    return {"version": "1.0.0", "tasks": TASK_CATALOG, "age_profiles": AGE_PROFILES,
            "difficulties": DIFFICULTIES}


class AttentionTaskService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._session_id: int | None = None
        self._trial_number = 0
        self._total_trials = 30
        self._target_probability = 0.30
        self._current_trial_id: int | None = None
        self._run_id: int | None = None
        self._task_key = "target_tap"
        self._age_profile = "child"
        self._difficulty = "moderate"
        self._display_ms = 1000
        self._intertrial_ms = 700
        self._display_token: str | None = None
        self._display_token_expires = 0.0
        self._display_phase = "waiting"
        self._practice_generation = 0
        self._last_display_seen = 0.0
        self._practice_session_id: int | None = None
        self._display_session_id: int | None = None
        self._random_seed: int | None = None
        self._rng = random.Random()
        self._trial_plan: list[bool] = []

    def pair_display(self, ttl_seconds: int = 1800) -> dict[str, object]:
        """Issue one short-lived capability for the participant-only display."""
        with self._lock:
            if self._display_phase in {"practice", "recording"} and self._display_session_id == session_manager.active_session_id and self._display_token and time.monotonic() < self._display_token_expires:
                return {"token": self._display_token, "expires_in_seconds": int(self._display_token_expires - time.monotonic())}
            self._display_token = secrets.token_urlsafe(24)
            self._display_session_id = session_manager.active_session_id
            self._display_token_expires = time.monotonic() + ttl_seconds
            self._display_phase = "waiting"
            self._last_display_seen = 0.0
            return {"token": self._display_token, "expires_in_seconds": ttl_seconds}

    def validate_display_token(self, token: str, *, mark_seen: bool = True) -> bool:
        with self._lock:
            valid = bool(self._display_token and time.monotonic() < self._display_token_expires
                         and (self._display_session_id is None or self._display_session_id == session_manager.active_session_id)
                         and secrets.compare_digest(token, self._display_token))
            if valid and mark_seen:
                self._last_display_seen = time.monotonic()
            return valid

    def prepare_practice(self, *, task_key: str, age_profile: str, difficulty: str) -> dict[str, object]:
        if session_manager.active_session_id is None:
            raise AttentionTaskConflict("Start the participant monitoring session before practice")
        if not self._display_token or time.monotonic() >= self._display_token_expires:
            raise AttentionTaskConflict("Create a fresh participant-display pairing before practice")
        if self._display_session_id is not None and self._display_session_id != session_manager.active_session_id:
            raise AttentionTaskConflict("Pair the display again for the current participant")
        if task_key not in TASK_CATALOG or age_profile not in AGE_PROFILES or difficulty not in DIFFICULTIES:
            raise AttentionTaskConflict("Unknown practice configuration")
        with self._lock:
            if self._run_id is not None and self._display_phase != "complete":
                raise AttentionTaskConflict("End the active recorded task before starting new practice")
            if self._display_phase == "complete":
                self._run_id = None
                self._session_id = None
                self._current_trial_id = None
                self._trial_number = 0
            self._task_key, self._age_profile, self._difficulty = task_key, age_profile, difficulty
            self._practice_generation += 1
            self._practice_session_id = session_manager.active_session_id
            self._display_session_id = self._practice_session_id
            self._display_phase = "practice"
            return self.public_status()

    def complete_practice(self, generation: int | None = None) -> dict[str, object]:
        with self._lock:
            if self._display_phase != "practice" or getattr(self, "_practice_session_id", None) != session_manager.active_session_id:
                raise AttentionTaskConflict("Start practice for the current participant before completing it")
            if generation is not None and generation != self._practice_generation:
                raise AttentionTaskConflict("Practice changed. Reload the participant screen and complete the current practice")
            self._display_phase = "ready"
        return self.public_status()

    def cancel_practice(self, generation: int | None = None) -> dict[str, object]:
        with self._lock:
            if generation is not None and generation != self._practice_generation:
                raise AttentionTaskConflict("Practice changed. Reload the participant screen")
            if self._display_phase != "practice":
                raise AttentionTaskConflict("No practice is active")
            self._display_phase = "waiting"
            self._practice_session_id = None
            return self.public_status()

    def recover_display(self) -> dict[str, object]:
        """Retry an unfinished displayed trial after a browser refresh or reconnect."""
        with self._lock:
            if self._current_trial_id is not None:
                with SessionLocal() as db:
                    db.execute(delete(AttentionTrial).where(AttentionTrial.id == self._current_trial_id))
                    db.commit()
                self._current_trial_id = None
                self._trial_number = max(0, self._trial_number - 1)
            return self.public_status()

    def public_status(self) -> dict[str, object]:
        with self._lock:
            return {"phase": self._display_phase, "practice_generation": self._practice_generation,
                    "display_connected": bool(self._last_display_seen and time.monotonic() - self._last_display_seen < 8),
                    "run_id": self._run_id, "task_key": self._task_key,
                    "age_profile": self._age_profile, "difficulty": self._difficulty,
                    "trial_number": self._trial_number, "total_trials": self._total_trials,
                    "complete": self._display_phase == "complete"}

    def start(self, total_trials: int = 30, target_probability: float = 0.30, *,
              task_key: str = "target_tap", age_profile: str = "child",
              difficulty: str = "moderate") -> dict[str, object]:
        session_id = session_manager.active_session_id
        if session_id is None:
            raise AttentionTaskConflict("Start a monitoring session before the attention task")
        if task_key not in TASK_CATALOG: raise AttentionTaskConflict("Unknown participant task")
        if age_profile not in AGE_PROFILES: raise AttentionTaskConflict("Unknown age profile")
        if difficulty not in DIFFICULTIES: raise AttentionTaskConflict("Unknown difficulty")
        if not self._display_token or time.monotonic() >= self._display_token_expires:
            raise AttentionTaskConflict("Create a fresh participant-display pairing before recording")
        if not settings.mock_mode and (
            self._display_phase != "ready"
            or getattr(self, "_practice_session_id", None) != session_id
            or (task_key, age_profile, difficulty) != (self._task_key, self._age_profile, self._difficulty)
        ):
            raise AttentionTaskConflict("Complete practice for this participant, activity and level before recording")
        with self._lock:
            if self._session_id == session_id and self._run_id is not None:
                raise AttentionTaskConflict("An attention task is already active. Complete or end it before starting another.")
        preset = DIFFICULTIES[difficulty]
        if difficulty in {"easy", "moderate", "hard", "standard"}:
            total_trials = int(preset["trials"]); target_probability = float(preset["target_probability"])
        seed = secrets.randbits(31)
        rng = random.Random(seed)
        target_count = max(1, min(total_trials - 1, round(total_trials * target_probability)))
        trial_plan = self._balanced_trial_plan(total_trials, target_count, rng)
        with SessionLocal() as db:
            session = db.get(MonitoringSession, session_id)
            run = AttentionTaskRun(session_id=session_id, participant_id=session.participant_id,
                task_key=task_key, task_version="1.1.0", age_profile=age_profile,
                difficulty=difficulty, configuration_json=json.dumps({**preset,
                "task": TASK_CATALOG[task_key], "age": AGE_PROFILES[age_profile],
                "random_seed": seed, "target_count": target_count,
                "target_sequence": trial_plan, "maximum_consecutive_targets": 3}, sort_keys=True))
            db.add(run); db.commit(); db.refresh(run); run_id = run.id
        with self._lock:
            self._session_id = session_id
            self._display_session_id = session_id
            self._trial_number = 0
            self._total_trials = total_trials
            self._target_probability = target_probability
            self._current_trial_id = None
            self._run_id = run_id; self._task_key = task_key; self._age_profile = age_profile
            self._difficulty = difficulty; self._display_ms = int(preset["display_ms"])
            self._intertrial_ms = int(preset["intertrial_ms"])
            self._random_seed = seed
            self._rng = rng
            self._trial_plan = trial_plan
            self._display_phase = "recording"
        session_manager.set_phase("task")
        return self.status()

    def next_trial(self) -> dict[str, object]:
        with self._lock:
            self._require_active()
            if self._current_trial_id is not None:
                raise AttentionTaskConflict("Complete the current trial first")
            if self._trial_number >= self._total_trials:
                raise AttentionTaskConflict("Attention task is complete")
            self._trial_number += 1
            is_target = self._trial_plan[self._trial_number - 1]
            stimulus_data = self._build_stimulus(is_target)
            stimulus = str(stimulus_data["code"])
            session_seconds = session_manager.elapsed()
            with SessionLocal() as db:
                trial = AttentionTrial(
                    session_id=self._session_id, task_run_id=self._run_id, trial_number=self._trial_number,
                    stimulus=stimulus, is_target=is_target,
                    stimulus_at=datetime.now(timezone.utc), stimulus_session_seconds=session_seconds,
                )
                db.add(trial)
                db.commit()
                db.refresh(trial)
                self._current_trial_id = trial.id
            return {"id": trial.id, "trial_number": trial.trial_number, "total_trials": self._total_trials,
                    "stimulus": stimulus, "is_target": is_target, "session_seconds": session_seconds,
                    "display_ms": self._display_ms, "intertrial_ms": self._intertrial_ms,
                    "task_key": self._task_key, "stimulus_data": stimulus_data}

    def _build_stimulus(self, is_target: bool) -> dict[str, object]:
        """Create task-specific, auditable stimulus metadata for the current trial."""
        if self._task_key == "go_no_go":
            return {"code": "GO" if is_target else "STOP", "label": "GO" if is_target else "STOP"}
        if self._task_key == "focus_match":
            shapes = ["◆", "●", "■", "▲"]
            left = self._rng.choice(shapes)
            right = left if is_target else self._rng.choice([item for item in shapes if item != left])
            return {"code": "MATCH" if is_target else "DIFFERENT", "items": [left, right]}
        if self._task_key == "visual_search":
            count = 5 if self._difficulty == "easy" else 8 if self._difficulty in {"moderate", "standard"} else 12
            items = ["●"] * count
            target_index = self._rng.randrange(count) if is_target else None
            if target_index is not None: items[target_index] = "★"
            return {"code": "ODD" if is_target else "SAME", "items": items, "target_index": target_index}
        if self._task_key == "pattern_memory":
            reference = [self._rng.randint(1, 4) for _ in range(3)]
            probe = list(reference)
            if not is_target:
                position = self._rng.randrange(len(probe)); choices = [n for n in range(1, 5) if n != probe[position]]
                probe[position] = self._rng.choice(choices)
            return {"code": "PATTERN_MATCH" if is_target else "PATTERN_CHANGE",
                    "reference": reference, "probe": probe, "delay_ms": 500}
        return {"code": "STAR" if is_target else "CIRCLE", "symbol": "★" if is_target else "●"}

    def complete_trial(self, trial_id: int, responded: bool, reaction_time_ms: float | None) -> dict[str, object]:
        with self._lock:
            self._require_active()
            if responded and (reaction_time_ms is None or not 0 <= reaction_time_ms <= self._display_ms):
                raise AttentionTaskConflict("Response time must fall within the displayed stimulus window")
            if trial_id != self._current_trial_id:
                raise AttentionTaskConflict("Trial is not current or was already completed")
            with SessionLocal() as db:
                trial = db.get(AttentionTrial, trial_id)
                if trial is None or trial.session_id != self._session_id:
                    raise AttentionTaskConflict("Trial not found for active session")
                score = score_trial(trial.is_target, responded)
                trial.responded = responded
                trial.correct = score.correct
                trial.incorrect = score.incorrect
                trial.missed = score.missed
                trial.false_response = score.false_response
                if responded:
                    trial.response_at = datetime.now(timezone.utc)
                    trial.response_session_seconds = session_manager.elapsed()
                    trial.reaction_time_ms = reaction_time_ms
                db.commit()
            self._current_trial_id = None
            if self._trial_number >= self._total_trials and self._run_id is not None:
                with SessionLocal() as db:
                    run = db.get(AttentionTaskRun, self._run_id)
                    if run: run.status="completed"; run.completed_at=datetime.now(timezone.utc); db.commit()
                self._display_phase = "complete"
                session_manager.set_phase("post_task")
            result = self.summary(self._session_id)
            result.update({"trial_id": trial_id, "trial_correct": score.correct,
                           "trial_incorrect": score.incorrect, "trial_missed": score.missed,
                           "trial_false_response": score.false_response})
            return result

    def status(self) -> dict[str, object]:
        with self._lock:
            return {"session_id": self._session_id, "run_id": self._run_id,
                    "task_key": self._task_key, "age_profile": self._age_profile,
                    "difficulty": self._difficulty, "trial_number": self._trial_number,
                    "total_trials": self._total_trials, "active_trial_id": self._current_trial_id,
                      "complete": self._trial_number >= self._total_trials and self._current_trial_id is None}

    def pause(self) -> dict[str, object]:
        """Request a safe participant-display pause between stimuli."""
        with self._lock:
            if self._display_phase != "recording" or self._run_id is None:
                raise AttentionTaskConflict("No recorded activity is running")
            self._display_phase = "paused"
            return self.public_status()

    def resume(self) -> dict[str, object]:
        with self._lock:
            if self._display_phase != "paused" or self._run_id is None:
                raise AttentionTaskConflict("The recorded activity is not paused")
            self._display_phase = "recording"
            return self.public_status()

    def abort(self) -> dict[str, object]:
        """Stop the current task and discard only an unfinished active trial."""
        with self._lock:
            session_id = self._session_id
            if self._current_trial_id is not None:
                with SessionLocal() as db:
                    db.execute(delete(AttentionTrial).where(AttentionTrial.id == self._current_trial_id))
                    db.commit()
            self._session_id = None
            self._trial_number = 0
            self._current_trial_id = None
            if self._run_id is not None:
                with SessionLocal() as db:
                    run=db.get(AttentionTaskRun,self._run_id)
                    if run and run.status != "completed":
                        run.status="aborted"; run.completed_at=datetime.now(timezone.utc); db.commit()
            self._run_id = None
            self._display_phase = "waiting"
            self._practice_session_id = None
            self._trial_plan = []
            if session_id is not None:
                session_manager.set_phase("post_task")
            return {"aborted": True, "session_id": session_id}

    @staticmethod
    def _balanced_trial_plan(total: int, target_count: int, rng: random.Random) -> list[bool]:
        """Return an exact-count plan with no more than three consecutive targets."""
        if not 0 <= target_count <= total:
            raise ValueError("target_count must be within the trial count")
        plan = [True] * target_count + [False] * (total - target_count)
        for _ in range(500):
            rng.shuffle(plan)
            if "1111" not in "".join("1" if value else "0" for value in plan):
                return list(plan)
        # Deterministic fallback: spread targets across the sequence.
        result = [False] * total
        for index in range(target_count):
            position = min(total - 1, round(index * (total - 1) / max(target_count - 1, 1)))
            while position < total and result[position]:
                position += 1
            if position >= total:
                position = next(i for i, value in enumerate(result) if not value)
            result[position] = True
        return result

    def summary(self, session_id: int) -> dict[str, object]:
        with SessionLocal() as db:
            trials = list(db.scalars(select(AttentionTrial).where(AttentionTrial.session_id == session_id)
                                     .order_by(AttentionTrial.trial_number)))
        completed = [item for item in trials if item.correct or item.incorrect]
        reaction_times = [item.reaction_time_ms for item in completed if item.reaction_time_ms is not None and item.is_target]
        total = len(completed)
        correct = sum(item.correct for item in completed)
        return {
            "session_id": session_id, "total_trials": total, "correct": correct,
            "incorrect": sum(item.incorrect for item in completed),
            "missed": sum(item.missed for item in completed),
            "false_responses": sum(item.false_response for item in completed),
            "accuracy": round(correct * 100 / total, 1) if total else 0.0,
            "average_reaction_time_ms": round(statistics.mean(reaction_times), 1) if reaction_times else None,
            "reaction_time_variability_ms": round(statistics.pstdev(reaction_times), 1) if len(reaction_times) > 1 else 0.0,
        }

    def _require_active(self) -> None:
        if self._session_id is None or self._session_id != session_manager.active_session_id:
            raise AttentionTaskConflict("Attention task is not attached to the active session")


attention_task_service = AttentionTaskService()
