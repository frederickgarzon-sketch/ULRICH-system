"""Synchronized session clock and derived-measurement persistence."""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timezone

from app.config import settings
from app.database.database import SessionLocal
from app.database.models import (
    BlinkEvent, BodyMovementEvent, BodyMovementSample, HeadMovementEvent,
    HeadPoseSample, MonitoringSession, PostureEvent, SessionSummary,
    TrackingValiditySample, SessionPhaseEvent,
)
from app.services.body_analysis_service import body_analysis_service
from app.services.face_analysis_service import face_analysis_service
from app.services.landmark_config import parse_groups, snapshot as landmark_config_snapshot
from app.services.calibration_service import accepted_snapshot as accepted_calibration_snapshot

logger = logging.getLogger(__name__)


class SessionConflict(RuntimeError):
    pass


class SessionManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._active_id: int | None = None
        self._started_monotonic = 0.0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_blinks = 0
        self._last_head_events = 0
        self._last_body_events = 0
        self._last_posture_events = 0
        self._phase = "baseline"

    @property
    def active_session_id(self) -> int | None:
        with self._lock:
            return self._active_id

    def elapsed(self) -> float:
        with self._lock:
            return round(time.monotonic() - self._started_monotonic, 3) if self._active_id else 0.0

    def start(self, participant_id: int, notes: str | None = None,
              operator_id: int | None = None) -> MonitoringSession:
        with self._lock:
            if self._active_id is not None:
                raise SessionConflict("A monitoring session is already active")
            with SessionLocal() as db:
                session = MonitoringSession(
                    participant_id=participant_id, mode=settings.app_mode, status="active",
                    notes=notes, operator_id=operator_id
                )
                db.add(session)
                db.commit()
                db.refresh(session)
                db.expunge(session)
            self._active_id = session.id
            self._started_monotonic = time.monotonic()
            self._phase = "baseline"
            with SessionLocal() as db:
                db.add(SessionPhaseEvent(session_id=session.id, session_seconds=0.0, phase="baseline"))
                db.commit()
            face = face_analysis_service.snapshot()
            body = body_analysis_service.snapshot()
            self._last_blinks = int(face["total_blinks"])
            self._last_head_events = int(face["head_movements"])
            self._last_body_events = int(body["movement_events"])
            self._last_posture_events = int(body["posture_changes"])
            self._stop.clear()
            self._thread = threading.Thread(target=self._record_loop, name="session-recorder", daemon=True)
            self._thread.start()
            logger.info("Session %s started for participant %s", session.id, participant_id)
            return session

    def set_phase(self, phase: str) -> None:
        if phase not in {"baseline", "task", "post_task"}:
            raise ValueError("Unknown session phase")
        with self._lock:
            if self._active_id is None or self._phase == phase:
                return
            self._phase = phase
            session_id = self._active_id
            elapsed = self.elapsed()
        with SessionLocal() as db:
            db.add(SessionPhaseEvent(session_id=session_id, session_seconds=elapsed, phase=phase))
            db.commit()

    def stop(self, session_id: int, notes: str | None = None) -> SessionSummary:
        with self._lock:
            if self._active_id != session_id:
                raise SessionConflict("Requested session is not the active session")
            duration = self.elapsed()
            self._stop.set()
            if self._thread:
                self._thread.join(timeout=3)
            face = face_analysis_service.snapshot()
            body = body_analysis_service.snapshot()
            from app.tasks.attention_task import attention_task_service
            attention = attention_task_service.summary(session_id)
            face_groups = parse_groups(settings.face_measure_groups)
            body_groups = parse_groups(settings.body_measure_groups)
            features = parse_groups(settings.feature_types)
            with SessionLocal() as db:
                session = db.get(MonitoringSession, session_id)
                if session is None:
                    raise SessionConflict("Session record not found")
                payload = {"face": face, "body": body, "attention": attention, "mode": settings.app_mode,
                           "landmark_configuration": landmark_config_snapshot(),
                           "calibration_profile": accepted_calibration_snapshot(session.participant_id)}
                session.status = "completed"
                session.end_time = datetime.now(timezone.utc)
                if notes is not None:
                    session.notes = notes
                summary = SessionSummary(
                    session_id=session_id, duration_seconds=duration,
                    total_blinks=int(face["total_blinks"]) if "eyes" in face_groups else 0,
                    average_blink_rate=float(face["blink_rate"]) if "eyes" in face_groups else 0,
                    head_movements=int(face["head_movements"]) if "head_pose" in face_groups else 0,
                    body_movement_events=int(body["movement_events"]) if body_groups else 0,
                    posture_changes=int(body["posture_changes"]) if body_groups and "angle" in features else 0,
                    mock_data=settings.mock_mode, summary_json=json.dumps(payload),
                )
                db.add(summary)
                db.commit()
                db.refresh(summary)
                db.expunge(summary)
            self._active_id = None
            self._started_monotonic = 0.0
            self._phase = "baseline"
            logger.info("Session %s stopped after %.1f seconds", session_id, duration)
            return summary

    def shutdown(self) -> None:
        """Finalize an active session during an orderly server shutdown."""
        session_id = self.active_session_id
        if session_id is None:
            return
        try:
            self.stop(session_id, "Automatically finalized during server shutdown.")
        except Exception:
            logger.exception("Unable to finalize active session %s during shutdown", session_id)

    def _record_loop(self) -> None:
        while not self._stop.wait(1.0):
            try:
                self._record_snapshot()
            except Exception:
                logger.exception("Unable to persist monitoring snapshot")

    def _record_snapshot(self) -> None:
        with self._lock:
            session_id = self._active_id
            elapsed = self.elapsed()
            phase = self._phase
        if session_id is None:
            return
        face = face_analysis_service.snapshot()
        body = body_analysis_service.snapshot()
        face_groups = parse_groups(settings.face_measure_groups)
        body_groups = parse_groups(settings.body_measure_groups)
        features = parse_groups(settings.feature_types)
        now = datetime.now(timezone.utc)
        with SessionLocal() as db:
            face_valid = bool(face.get("tracking"))
            eyes_valid = face_valid and face.get("average_ear") is not None
            head_valid = face_valid and all(face.get(axis) is not None for axis in ("yaw", "pitch", "roll"))
            body_valid = bool(body.get("tracking") and body.get("person_count") == 1 and body.get("required_joints_visible"))
            db.add(TrackingValiditySample(
                session_id=session_id, sampled_at=now, session_seconds=elapsed, phase=phase,
                face_valid=face_valid, eyes_valid=eyes_valid, head_valid=head_valid, body_valid=body_valid,
                face_status=str(face.get("status") or "UNKNOWN"), body_status=str(body.get("status") or "UNKNOWN"),
            ))
            if "head_pose" in face_groups and ({"position", "angle"} & features):
                db.add(HeadPoseSample(session_id=session_id, sampled_at=now, session_seconds=elapsed,
                                      yaw=face.get("yaw"), pitch=face.get("pitch"), roll=face.get("roll"),
                                      valid=head_valid, status=str(face.get("status") or "UNKNOWN"), phase=phase))
            if body_groups and ({"position", "velocity", "normalized_movement"} & features):
                db.add(BodyMovementSample(session_id=session_id, sampled_at=now, session_seconds=elapsed,
                                          magnitude=float(body.get("movement_magnitude") or 0.0),
                                          regional_json=json.dumps(body.get("regional_movement") or {}),
                                          valid=body_valid, status=str(body.get("status") or "UNKNOWN"), phase=phase))
            if "eyes" in face_groups and "frequency" in features and int(face["total_blinks"]) > self._last_blinks:
                db.add(BlinkEvent(session_id=session_id, occurred_at=now, session_seconds=elapsed,
                                  average_ear=face.get("last_blink_minimum_ear"),
                                  closure_duration_seconds=face.get("last_blink_duration_seconds"), phase=phase))
                self._last_blinks = int(face["total_blinks"])
            if "head_pose" in face_groups and "frequency" in features and int(face["head_movements"]) > self._last_head_events:
                db.add(HeadMovementEvent(session_id=session_id, occurred_at=now, session_seconds=elapsed,
                                         direction=str(face["head_direction"]),
                                         magnitude=float(face["head_movement_magnitude"]), phase=phase))
                self._last_head_events = int(face["head_movements"])
            if body_groups and "frequency" in features and int(body["movement_events"]) > self._last_body_events:
                db.add(BodyMovementEvent(session_id=session_id, occurred_at=now, session_seconds=elapsed,
                                         magnitude=float(body["movement_magnitude"]), phase=phase))
                self._last_body_events = int(body["movement_events"])
            if body_groups and "angle" in features and int(body["posture_changes"]) > self._last_posture_events:
                db.add(PostureEvent(session_id=session_id, occurred_at=now, session_seconds=elapsed,
                                    posture_angle=body["posture_angle"], phase=phase))
                self._last_posture_events = int(body["posture_changes"])
            db.commit()


session_manager = SessionManager()
