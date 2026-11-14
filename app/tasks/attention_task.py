"""Colorful, count-to-completion Pop the Balloon research task."""

from __future__ import annotations

import json
import random
import secrets
import statistics
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select

from app.config import settings
from app.database.database import SessionLocal
from app.database.models import AttentionTaskRun, AttentionTrial, MonitoringSession
from app.sessions.session_manager import session_manager


TASK_VERSION = "2.0.0-balloon"
BALLOON_COLORS = {
    "coral": {"label": "Coral", "hex": "#F45B69"},
    "sky": {"label": "Sky blue", "hex": "#2F9FE8"},
    "turquoise": {"label": "Turquoise", "hex": "#18BFC1"},
    "yellow": {"label": "Sunny yellow", "hex": "#F7C948"},
    "purple": {"label": "Purple", "hex": "#9857E5"},
    "orange": {"label": "Orange", "hex": "#F58A3A"},
    "green": {"label": "Green", "hex": "#54B948"},
    "pink": {"label": "Pink", "hex": "#EE70B7"},
}
GAME_MODES = {
    "any": {"name": "Pop any balloon", "instruction": "Tap each balloon to pop it."},
    "target_color": {"name": "Pop the target color", "instruction": "Pop only the requested color."},
}
TASK_CATALOG = {
    "pop_balloon": {
        "name": "Pop the Balloon",
        "description": "Pop the required number of balloons to complete the activity.",
        "best_for": ["child", "preteen", "teen", "adult"],
        "instruction": "Tap the balloon to pop it!",
        "version": TASK_VERSION,
    }
}
AGE_PROFILES = {
    "child": {"name": "Child", "ages": "6–9", "recommended_pops": 15, "recommended_difficulty": "easy"},
    "preteen": {"name": "Pre-teen", "ages": "10–12", "recommended_pops": 20, "recommended_difficulty": "moderate"},
    "teen": {"name": "Teen", "ages": "13–17", "recommended_pops": 30, "recommended_difficulty": "moderate"},
    "adult": {"name": "Adult", "ages": "18+", "recommended_pops": 30, "recommended_difficulty": "standard"},
}
DIFFICULTIES = {
    "easy": {"display_ms": 2200, "intertrial_ms": [350, 550], "target_probability": 1.0,
             "size_px": 176, "speed": "slow", "default_mode": "any"},
    "moderate": {"display_ms": 1600, "intertrial_ms": [450, 750], "target_probability": .62,
                 "size_px": 148, "speed": "normal", "default_mode": "target_color"},
    "hard": {"display_ms": 1150, "intertrial_ms": [350, 850], "target_probability": .55,
             "size_px": 120, "speed": "fast", "default_mode": "target_color"},
    "standard": {"display_ms": 1600, "intertrial_ms": [450, 750], "target_probability": .62,
                 "size_px": 148, "speed": "normal", "default_mode": "target_color"},
}


@dataclass(frozen=True, slots=True)
class TrialScore:
    correct: bool
    incorrect: bool
    missed: bool
    false_response: bool


def score_trial(is_target: bool, responded: bool) -> TrialScore:
    correct = (is_target and responded) or (not is_target and not responded)
    return TrialScore(correct, not correct, is_target and not responded, not is_target and responded)


class AttentionTaskConflict(RuntimeError):
    pass


def task_catalog() -> dict[str, object]:
    return {
        "version": TASK_VERSION, "tasks": TASK_CATALOG, "age_profiles": AGE_PROFILES,
        "difficulties": DIFFICULTIES, "game_modes": GAME_MODES, "colors": BALLOON_COLORS,
        "goal_presets": [10, 15, 20, 30],
        "goal_range": {"minimum": 5, "maximum": 50, "default": 20},
        "practice_balloon_count": 5, "maximum_duration_seconds": 300,
    }


class AttentionTaskService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._session_id: int | None = None
        self._trial_number = 0; self._total_trials = 60
        self._required_pops = 20; self._correct_pops = 0
        self._current_trial_id: int | None = None; self._run_id: int | None = None
        self._task_key = "pop_balloon"; self._age_profile = "child"; self._difficulty = "easy"
        self._game_mode = "any"; self._target_color = "sky"; self._sound_enabled = True
        self._display_ms = 2200; self._maximum_duration_seconds = 300
        self._display_token: str | None = None; self._display_token_expires = 0.0
        self._display_phase = "waiting"; self._practice_generation = 0
        self._practice_notice = ""
        self._practice_seed: int | None = None; self._practice_stimuli: list[dict[str, Any]] = []
        self._last_display_seen = 0.0; self._practice_session_id: int | None = None
        self._display_session_id: int | None = None; self._random_seed: int | None = None
        self._rng = random.Random(); self._stimulus_plan: list[dict[str, Any]] = []
        self._termination_reason: str | None = None; self._resumed_since_trial = False
        self._auto_paused = False

    def pair_display(self, ttl_seconds: int = 1800) -> dict[str, object]:
        with self._lock:
            if (self._display_phase in {"practice", "ready", "recording", "paused"}
                    and self._display_session_id == session_manager.active_session_id
                    and self._display_token and time.monotonic() < self._display_token_expires):
                return {"token": self._display_token,
                        "expires_in_seconds": int(self._display_token_expires - time.monotonic())}
            self._display_token = secrets.token_urlsafe(24)
            self._display_session_id = session_manager.active_session_id
            self._display_token_expires = time.monotonic() + ttl_seconds
            self._display_phase = "waiting"; self._last_display_seen = 0.0
            self._practice_notice = ""
            return {"token": self._display_token, "expires_in_seconds": ttl_seconds}

    def validate_display_token(self, token: str, *, mark_seen: bool = True) -> bool:
        with self._lock:
            valid = bool(self._display_token and time.monotonic() < self._display_token_expires
                         and (self._display_session_id is None
                              or self._display_session_id == session_manager.active_session_id)
                         and secrets.compare_digest(token, self._display_token))
            if valid and mark_seen: self._last_display_seen = time.monotonic()
            return valid

    @staticmethod
    def _validate_configuration(age_profile: str, difficulty: str, game_mode: str,
                                target_color: str, required_pops: int,
                                maximum_duration_seconds: int) -> None:
        if age_profile not in AGE_PROFILES: raise AttentionTaskConflict("Unknown age profile")
        if difficulty not in DIFFICULTIES: raise AttentionTaskConflict("Unknown difficulty")
        if game_mode not in GAME_MODES: raise AttentionTaskConflict("Unknown balloon game mode")
        if target_color not in BALLOON_COLORS: raise AttentionTaskConflict("Unknown target color")
        if not 5 <= required_pops <= 50: raise AttentionTaskConflict("Balloon goal must be between 5 and 50")
        if not 60 <= maximum_duration_seconds <= 600:
            raise AttentionTaskConflict("Maximum duration must be between 1 and 10 minutes")
        if difficulty == "easy" and game_mode != "any":
            raise AttentionTaskConflict("Easy mode uses Pop any balloon")

    def prepare_practice(self, *, task_key: str = "pop_balloon", age_profile: str,
                         difficulty: str, game_mode: str | None = None, target_color: str = "sky",
                         required_pops: int = 20, sound_enabled: bool = True,
                         maximum_duration_seconds: int = 300) -> dict[str, object]:
        if session_manager.active_session_id is None:
            raise AttentionTaskConflict("Start the participant monitoring session before practice")
        if not self._display_token or time.monotonic() >= self._display_token_expires:
            raise AttentionTaskConflict("Create a fresh participant-display pairing before practice")
        if self._display_session_id is not None and self._display_session_id != session_manager.active_session_id:
            raise AttentionTaskConflict("Pair the display again for the current participant")
        if task_key != "pop_balloon":
            raise AttentionTaskConflict("Pop the Balloon is the supported participant activity")
        mode = game_mode or str(DIFFICULTIES.get(difficulty, {}).get("default_mode", "any"))
        self._validate_configuration(age_profile, difficulty, mode, target_color,
                                     required_pops, maximum_duration_seconds)
        with self._lock:
            if self._run_id is not None and self._display_phase != "complete":
                raise AttentionTaskConflict("End the active recorded task before starting new practice")
            if self._display_phase == "complete":
                self._run_id = None; self._session_id = None; self._current_trial_id = None; self._trial_number = 0
            self._task_key, self._age_profile, self._difficulty = task_key, age_profile, difficulty
            self._game_mode, self._target_color = mode, target_color
            self._required_pops, self._sound_enabled = required_pops, bool(sound_enabled)
            self._maximum_duration_seconds = maximum_duration_seconds; self._practice_generation += 1
            self._practice_seed = secrets.randbits(31); practice_rng = random.Random(self._practice_seed)
            self._practice_notice = ""
            self._practice_stimuli = self._build_stimulus_plan(
                5, min(3, required_pops), difficulty, mode, target_color, practice_rng, practice=True)
            self._practice_session_id = session_manager.active_session_id
            self._display_session_id = self._practice_session_id; self._display_phase = "practice"
            return self.public_status()

    def complete_practice(self, generation: int | None = None) -> dict[str, object]:
        with self._lock:
            if self._display_phase != "practice" or self._practice_session_id != session_manager.active_session_id:
                raise AttentionTaskConflict("Start practice for the current participant before completing it")
            if generation is not None and generation != self._practice_generation:
                raise AttentionTaskConflict("Practice changed. Reload and complete the current practice")
            self._display_phase = "ready"; return self.public_status()

    def cancel_practice(self, generation: int | None = None) -> dict[str, object]:
        with self._lock:
            if generation is not None and generation != self._practice_generation:
                raise AttentionTaskConflict("Practice changed. Reload the participant screen")
            if self._display_phase != "practice": raise AttentionTaskConflict("No practice is active")
            self._display_phase = "waiting"; self._practice_session_id = None; self._practice_stimuli = []
            return self.public_status()

    def recover_display(self) -> dict[str, object]:
        with self._lock:
            self._discard_unfinished_trial()
            return self.public_status()

    def practice_needs_help(self, generation: int | None = None) -> dict[str, object]:
        with self._lock:
            self.cancel_practice(generation)
            self._practice_notice = "Practice stopped after 3 tries. Ask the researcher for help, then restart practice."
            return self.public_status()

    def completed_trial_status(self, trial_id: int) -> dict[str, object]:
        """Reconcile a lost completion acknowledgement without replaying saved data."""
        with self._lock:
            with SessionLocal() as db:
                trial = db.get(AttentionTrial, trial_id)
                if (trial is None or trial.session_id != self._session_id
                        or trial.task_run_id != self._run_id):
                    raise AttentionTaskConflict("Trial is not part of the current game")
                completed = bool(trial.correct or trial.incorrect or trial.missed)
            return {**self.public_status(), "trial_id": trial_id, "completed": completed}

    def _discard_unfinished_trial(self) -> None:
        """Remove only an unfinished presentation so it can be replayed exactly."""
        if self._current_trial_id is None:
            return
        with SessionLocal() as db:
            db.execute(delete(AttentionTrial).where(AttentionTrial.id == self._current_trial_id)); db.commit()
        self._current_trial_id = None; self._trial_number = max(0, self._trial_number - 1)

    def public_status(self) -> dict[str, object]:
        with self._lock:
            connected = bool(self._last_display_seen and time.monotonic() - self._last_display_seen < 8)
            if self._display_phase == "recording" and not connected:
                self._discard_unfinished_trial(); self._display_phase = "paused"; self._auto_paused = True
            elif self._display_phase == "paused" and connected and self._auto_paused:
                self._display_phase = "recording"; self._auto_paused = False; self._resumed_since_trial = True
            return {"phase": self._display_phase, "practice_generation": self._practice_generation,
                    "practice_notice": self._practice_notice,
                    "practice_seed": self._practice_seed,
                    "practice_stimuli": self._practice_stimuli if self._display_phase == "practice" else [],
                    "display_connected": connected, "run_id": self._run_id,
                    "task_key": self._task_key, "task_version": TASK_VERSION,
                    "age_profile": self._age_profile, "difficulty": self._difficulty,
                    "game_mode": self._game_mode, "target_color": self._target_color,
                    "target_color_label": BALLOON_COLORS[self._target_color]["label"],
                    "sound_enabled": self._sound_enabled,
                    "maximum_duration_seconds": self._maximum_duration_seconds,
                    "trial_number": self._trial_number,
                    "total_trials": self._total_trials, "required_pops": self._required_pops,
                    "correct_pops": self._correct_pops,
                    "pause_reason": "connection_lost" if self._auto_paused else ("operator" if self._display_phase == "paused" else None),
                    "attempts_remaining": max(0, self._total_trials - self._trial_number),
                    "termination_reason": self._termination_reason,
                    "complete": self._display_phase == "complete"}

    def start(self, total_trials: int = 20, target_probability: float = .62, *,
              task_key: str = "pop_balloon", age_profile: str = "child", difficulty: str = "easy",
              required_pops: int | None = None, game_mode: str | None = None,
              target_color: str = "sky", sound_enabled: bool = True,
              maximum_duration_seconds: int = 300) -> dict[str, object]:
        session_id = session_manager.active_session_id
        if session_id is None: raise AttentionTaskConflict("Start a monitoring session before the balloon game")
        if task_key != "pop_balloon": raise AttentionTaskConflict("Pop the Balloon is the supported participant activity")
        preset = DIFFICULTIES.get(difficulty)
        if preset is None: raise AttentionTaskConflict("Unknown difficulty")
        goal = int(required_pops if required_pops is not None else total_trials)
        mode = game_mode or str(preset["default_mode"])
        self._validate_configuration(age_profile, difficulty, mode, target_color, goal, maximum_duration_seconds)
        if not self._display_token or time.monotonic() >= self._display_token_expires:
            raise AttentionTaskConflict("Create a fresh participant-display pairing before recording")
        if not settings.mock_mode and (self._display_phase != "ready" or self._practice_session_id != session_id
            or (task_key, age_profile, difficulty, mode, target_color, goal)
            != (self._task_key, self._age_profile, self._difficulty, self._game_mode,
                self._target_color, self._required_pops)):
            raise AttentionTaskConflict("Complete practice with this balloon configuration before recording")
        with self._lock:
            if self._session_id == session_id and self._run_id is not None:
                raise AttentionTaskConflict("A recorded balloon game is already active")
        max_attempts = goal * 3; seed = secrets.randbits(31); rng = random.Random(seed)
        plan = self._build_stimulus_plan(max_attempts, goal, difficulty, mode, target_color, rng, practice=False)
        configuration = {"task": TASK_CATALOG[task_key], "age": AGE_PROFILES[age_profile],
            "difficulty": preset, "game_mode": mode, "target_color": target_color,
            "target_color_label": BALLOON_COLORS[target_color]["label"],
            "required_correct_pops": goal, "maximum_attempts": max_attempts,
            "maximum_duration_seconds": maximum_duration_seconds, "sound_enabled": bool(sound_enabled),
            "random_seed": seed, "stimulus_sequence": plan, "maximum_consecutive_targets": 3}
        with SessionLocal() as db:
            session = db.get(MonitoringSession, session_id)
            run = AttentionTaskRun(session_id=session_id, participant_id=session.participant_id,
                task_key=task_key, task_version=TASK_VERSION, age_profile=age_profile,
                difficulty=difficulty, configuration_json=json.dumps(configuration, sort_keys=True))
            db.add(run); db.commit(); db.refresh(run); run_id = run.id
        with self._lock:
            self._session_id = session_id; self._display_session_id = session_id
            self._trial_number = 0; self._total_trials = max_attempts; self._required_pops = goal
            self._correct_pops = 0; self._current_trial_id = None; self._run_id = run_id
            self._task_key = task_key; self._age_profile = age_profile; self._difficulty = difficulty
            self._game_mode = mode; self._target_color = target_color; self._sound_enabled = bool(sound_enabled)
            self._display_ms = int(preset["display_ms"]); self._maximum_duration_seconds = maximum_duration_seconds
            self._random_seed = seed; self._rng = rng; self._stimulus_plan = plan
            self._termination_reason = None; self._resumed_since_trial = False; self._auto_paused = False
            self._display_phase = "recording"
        session_manager.set_phase("task"); return self.status()

    def _build_stimulus_plan(self, count: int, required_pops: int, difficulty: str,
                             game_mode: str, target_color: str, rng: random.Random,
                             *, practice: bool) -> list[dict[str, Any]]:
        preset = DIFFICULTIES[difficulty]
        if game_mode == "any": targets = [True] * count
        else:
            # Practice must demonstrate both "pop" and "wait". Recorded plans
            # contain enough targets to reach the goal without making the
            # distractor rule meaningless.
            target_count = 3 if practice and count >= 5 else min(
                count, max(required_pops + 3, round(count * float(preset["target_probability"])))
            )
            targets = self._balanced_trial_plan(count, target_count, rng)
        colors = list(BALLOON_COLORS); distractors = [item for item in colors if item != target_color]
        recent: list[str] = []; plan: list[dict[str, Any]] = []
        low_wait, high_wait = preset["intertrial_ms"]
        for index, is_target in enumerate(targets, start=1):
            choices = colors if game_mode == "any" else ([target_color] if is_target else distractors)
            available = [item for item in choices if len(recent) < 2 or not all(old == item for old in recent[-2:])]
            color = rng.choice(available or choices); recent.append(color)
            plan.append({"sequence": index, "code": f"BALLOON_{color.upper()}", "color": color,
                "color_label": BALLOON_COLORS[color]["label"], "color_hex": BALLOON_COLORS[color]["hex"],
                "target_color": target_color, "target_color_label": BALLOON_COLORS[target_color]["label"],
                "is_target": bool(is_target), "x_percent": round(rng.uniform(10, 84), 2),
                # Keep balloons fully inside the sky/play region, clear of the
                # fixed HUD and the decorative ground at the bottom.
                "y_percent": round(rng.uniform(14, 58), 2),
                "size_px": int(preset["size_px"] * rng.uniform(.92, 1.08)), "speed": preset["speed"],
                "display_ms": int(preset["display_ms"]),
                "intertrial_ms": rng.randint(int(low_wait), int(high_wait)), "practice": practice})
        return plan

    def next_trial(self) -> dict[str, object]:
        with self._lock:
            self._require_active()
            if self._display_phase != "recording": raise AttentionTaskConflict("The balloon game is paused or complete")
            if self._current_trial_id is not None: raise AttentionTaskConflict("Complete the current balloon first")
            if self._time_limit_reached():
                self._finish_run("time_limit"); raise AttentionTaskConflict("The game reached its safety time limit")
            if self._trial_number >= self._total_trials:
                self._finish_run("maximum_attempts"); raise AttentionTaskConflict("The game reached its safety attempt limit")
            metadata = dict(self._stimulus_plan[self._trial_number]); self._trial_number += 1
            metadata["pause_context"] = "resumed" if self._resumed_since_trial else "continuous"
            self._resumed_since_trial = False; metadata["tracking"] = self._tracking_snapshot()
            session_seconds = session_manager.elapsed()
            with SessionLocal() as db:
                trial = AttentionTrial(session_id=self._session_id, task_run_id=self._run_id,
                    trial_number=self._trial_number, stimulus=str(metadata["code"]),
                    stimulus_json=json.dumps(metadata, sort_keys=True), phase="recorded",
                    is_target=bool(metadata["is_target"]), stimulus_at=datetime.now(timezone.utc),
                    stimulus_session_seconds=session_seconds)
                db.add(trial); db.commit(); db.refresh(trial); self._current_trial_id = trial.id
            return {"id": trial.id, "trial_number": trial.trial_number, "total_trials": self._total_trials,
                    "required_pops": self._required_pops, "correct_pops": self._correct_pops,
                    "stimulus": trial.stimulus, "is_target": trial.is_target,
                    "session_seconds": session_seconds, "display_ms": metadata["display_ms"],
                    "intertrial_ms": metadata["intertrial_ms"], "task_key": self._task_key,
                    "stimulus_data": metadata}

    @staticmethod
    def _tracking_snapshot() -> dict[str, object]:
        try:
            from app.services.body_analysis_service import body_analysis_service
            from app.services.face_analysis_service import face_analysis_service
            face = face_analysis_service.snapshot(); body = body_analysis_service.snapshot()
            return {"face_valid": bool(face.get("tracking")), "body_valid": bool(body.get("tracking")),
                    "face_status": str(face.get("status", "UNKNOWN")),
                    "body_status": str(body.get("status", "UNKNOWN"))}
        except Exception:
            return {"face_valid": False, "body_valid": False,
                    "face_status": "UNAVAILABLE", "body_status": "UNAVAILABLE"}

    def complete_trial(self, trial_id: int, responded: bool, reaction_time_ms: float | None,
                       premature_taps: int = 0) -> dict[str, object]:
        with self._lock:
            self._require_active()
            if responded and (reaction_time_ms is None or not 0 <= reaction_time_ms <= self._display_ms):
                raise AttentionTaskConflict("Response time must fall within the balloon display window")
            if trial_id != self._current_trial_id:
                raise AttentionTaskConflict("Balloon is not current or was already completed")
            with SessionLocal() as db:
                trial = db.get(AttentionTrial, trial_id)
                if trial is None or trial.session_id != self._session_id:
                    raise AttentionTaskConflict("Balloon trial not found for the active session")
                score = score_trial(trial.is_target, responded)
                trial.responded = responded; trial.correct = score.correct; trial.incorrect = score.incorrect
                trial.missed = score.missed; trial.false_response = score.false_response
                trial.premature_taps = max(0, int(premature_taps))
                if responded:
                    trial.response_at = datetime.now(timezone.utc)
                    trial.response_session_seconds = session_manager.elapsed(); trial.reaction_time_ms = reaction_time_ms
                db.commit()
            self._current_trial_id = None; correct_pop = bool(trial.is_target and responded)
            if correct_pop: self._correct_pops += 1
            if self._correct_pops >= self._required_pops: self._finish_run("goal_reached")
            elif self._trial_number >= self._total_trials: self._finish_run("maximum_attempts")
            elif self._time_limit_reached(): self._finish_run("time_limit")
            result = self.summary(self._session_id)
            result.update({"trial_id": trial_id, "trial_correct": score.correct,
                "trial_incorrect": score.incorrect, "trial_missed": score.missed,
                "trial_false_response": score.false_response, "correct_pop": correct_pop,
                "correct_pops": self._correct_pops, "required_pops": self._required_pops,
                "phase": self._display_phase, "termination_reason": self._termination_reason})
            return result

    def _time_limit_reached(self) -> bool:
        if self._run_id is None: return False
        with SessionLocal() as db: run = db.get(AttentionTaskRun, self._run_id)
        if not run: return False
        started = run.started_at if run.started_at.tzinfo else run.started_at.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - started).total_seconds() >= self._maximum_duration_seconds

    def _finish_run(self, reason: str) -> None:
        if self._run_id is not None:
            with SessionLocal() as db:
                run = db.get(AttentionTaskRun, self._run_id)
                if run:
                    run.status = "completed" if reason == "goal_reached" else "incomplete"
                    run.termination_reason = reason; run.completed_at = datetime.now(timezone.utc); db.commit()
        self._termination_reason = reason; self._display_phase = "complete"; session_manager.set_phase("post_task")

    def status(self) -> dict[str, object]:
        with self._lock:
            return {"session_id": self._session_id, "run_id": self._run_id,
                    "task_key": self._task_key, "task_version": TASK_VERSION,
                    "age_profile": self._age_profile, "difficulty": self._difficulty,
                    "game_mode": self._game_mode, "target_color": self._target_color,
                    "trial_number": self._trial_number, "total_trials": self._total_trials,
                    "required_pops": self._required_pops, "correct_pops": self._correct_pops,
                    "active_trial_id": self._current_trial_id, "termination_reason": self._termination_reason,
                    "complete": self._display_phase == "complete"}

    def pause(self) -> dict[str, object]:
        with self._lock:
            if self._display_phase != "recording" or self._run_id is None:
                raise AttentionTaskConflict("No recorded balloon game is running")
            self._discard_unfinished_trial(); self._auto_paused = False
            self._display_phase = "paused"; return self.public_status()

    def resume(self) -> dict[str, object]:
        with self._lock:
            if self._display_phase != "paused" or self._run_id is None:
                raise AttentionTaskConflict("The balloon game is not paused")
            if not self._last_display_seen or time.monotonic() - self._last_display_seen >= 8:
                raise AttentionTaskConflict("Reconnect the participant screen before resuming")
            self._display_phase = "recording"; self._auto_paused = False
            self._resumed_since_trial = True; return self.public_status()

    def abort(self, reason: str = "operator_ended") -> dict[str, object]:
        with self._lock:
            session_id = self._session_id
            if self._current_trial_id is not None:
                with SessionLocal() as db:
                    db.execute(delete(AttentionTrial).where(AttentionTrial.id == self._current_trial_id)); db.commit()
            self._current_trial_id = None
            if self._run_id is not None:
                with SessionLocal() as db:
                    run = db.get(AttentionTaskRun, self._run_id)
                    if run and run.status not in {"completed", "incomplete"}:
                        run.status = "aborted"; run.termination_reason = reason[:80]
                        run.completed_at = datetime.now(timezone.utc); db.commit()
            self._run_id = None; self._display_phase = "waiting"; self._practice_session_id = None
            self._auto_paused = False
            self._stimulus_plan = []; self._termination_reason = reason
            if session_id is not None: session_manager.set_phase("post_task")
            return {"aborted": True, "session_id": session_id, "reason": reason}

    @staticmethod
    def _balanced_trial_plan(total: int, target_count: int, rng: random.Random) -> list[bool]:
        if not 0 <= target_count <= total: raise ValueError("target_count must be within the trial count")
        plan = [True] * target_count + [False] * (total - target_count)
        for _ in range(1000):
            rng.shuffle(plan)
            if "1111" not in "".join("1" if value else "0" for value in plan): return list(plan)
        result: list[bool] = []; targets_left, distractors_left = target_count, total - target_count
        while targets_left or distractors_left:
            if targets_left and (len(result) < 3 or not all(result[-3:])):
                result.append(True); targets_left -= 1
            elif distractors_left: result.append(False); distractors_left -= 1
            else: result.append(True); targets_left -= 1
        return result

    def summary(self, session_id: int) -> dict[str, object]:
        with SessionLocal() as db:
            trials = list(db.scalars(select(AttentionTrial).where(
                AttentionTrial.session_id == session_id).order_by(AttentionTrial.trial_number)))
            run = db.scalar(select(AttentionTaskRun).where(
                AttentionTaskRun.session_id == session_id).order_by(AttentionTaskRun.id.desc()).limit(1))
        completed = [item for item in trials if item.correct or item.incorrect or item.missed]
        target_responses = [item for item in completed if item.is_target and item.responded]
        reaction_times = [item.reaction_time_ms for item in target_responses if item.reaction_time_ms is not None]
        total = len(completed); correct_decisions = sum(bool(item.correct) for item in completed); config: dict[str, Any] = {}
        if run:
            try: config = json.loads(run.configuration_json)
            except (TypeError, json.JSONDecodeError): config = {}
        required = int(config.get("required_correct_pops", self._required_pops if self._session_id == session_id else 0))
        completion_seconds = None
        if run and run.completed_at:
            started = run.started_at if run.started_at.tzinfo else run.started_at.replace(tzinfo=timezone.utc)
            ended = run.completed_at if run.completed_at.tzinfo else run.completed_at.replace(tzinfo=timezone.utc)
            completion_seconds = round((ended - started).total_seconds(), 3)
        return {"session_id": session_id, "total_trials": total, "total_attempts": total,
            "required_pops": required, "correct_pops": len(target_responses), "correct": correct_decisions,
            "correct_rejections": sum(bool(not item.is_target and not item.responded) for item in completed),
            "incorrect": sum(bool(item.incorrect) for item in completed),
            "incorrect_pops": sum(bool(item.false_response) for item in completed),
            "missed": sum(bool(item.missed) for item in completed),
            "false_responses": sum(bool(item.false_response) for item in completed),
            "premature_taps": sum(int(item.premature_taps or 0) for item in completed),
            "accuracy": round(correct_decisions * 100 / total, 1) if total else 0.0,
            "average_reaction_time_ms": round(statistics.mean(reaction_times), 1) if reaction_times else None,
            "median_reaction_time_ms": round(statistics.median(reaction_times), 1) if reaction_times else None,
            "reaction_time_variability_ms": round(statistics.pstdev(reaction_times), 1) if len(reaction_times) > 1 else 0.0,
            "fastest_reaction_time_ms": round(min(reaction_times), 1) if reaction_times else None,
            "slowest_reaction_time_ms": round(max(reaction_times), 1) if reaction_times else None,
            "completion_seconds": completion_seconds, "task_status": run.status if run else None,
            "termination_reason": run.termination_reason if run else None,
            "goal_reached": bool(run and run.termination_reason == "goal_reached")}

    def _require_active(self) -> None:
        if self._session_id is None or self._session_id != session_manager.active_session_id:
            raise AttentionTaskConflict("Balloon game is not attached to the active session")


attention_task_service = AttentionTaskService()
