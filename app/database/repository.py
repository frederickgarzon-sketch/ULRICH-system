"""Database operations kept separate from HTTP and analysis code."""

from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from analysis.hemslnn_features import screening_summary
from app.database.database import SessionLocal
from app.database.models import (
    AttentionTrial, AttentionTaskRun, BlinkEvent, BodyMovementEvent, BodyMovementSample,
    HeadMovementEvent, HeadPoseSample, MonitoringSession, Participant,
    PostureEvent, SessionSummary, AuditEvent, CalibrationProfile,
    ResearchTaskRun, ResearchTaskTrial, UserAccount, CalibrationVerification, SystemSetupState,
    TrackingValiditySample, SessionPhaseEvent,
)


class DuplicateParticipantCode(ValueError):
    pass


class RecordDeleteConflict(ValueError):
    pass


class Repository:
    def get_system_setup_state(self) -> SystemSetupState | None:
        with SessionLocal() as db:
            item = db.get(SystemSetupState, 1)
            if item: db.expunge(item)
            return item

    def save_system_setup_state(self, *, status: str | None = None,
                                current_step: int | None = None,
                                progress_json: str | None = None,
                                configuration_hash: str | None = None,
                                calibration_version: str | None = None,
                                completed_by_user_id: int | None = None,
                                completed_by_name: str | None = None,
                                completed_at: datetime | None = None,
                                clear_completion: bool = False) -> SystemSetupState:
        with SessionLocal() as db:
            item = db.get(SystemSetupState, 1)
            if item is None:
                item = SystemSetupState(id=1)
                db.add(item)
            if status is not None: item.status = status
            if current_step is not None: item.current_step = current_step
            if progress_json is not None: item.progress_json = progress_json
            if configuration_hash is not None: item.configuration_hash = configuration_hash
            if calibration_version is not None: item.calibration_version = calibration_version
            if completed_by_user_id is not None: item.completed_by_user_id = completed_by_user_id
            if completed_by_name is not None: item.completed_by_name = completed_by_name
            if completed_at is not None: item.completed_at = completed_at
            if clear_completion:
                item.completed_at = None; item.completed_by_user_id = None
                item.completed_by_name = None; item.configuration_hash = None
                item.calibration_version = None
            item.updated_at = datetime.now(timezone.utc)
            db.commit(); db.refresh(item); db.expunge(item)
            return item

    def create_calibration_profile(self, *, name: str, participant_id: int | None,
                                   configuration_hash: str, configuration_json: str,
                                   results_json: str, manual_checks_json: str,
                                   notes: str | None, profile_type: str = "participant",
                                   created_by_user_id: int | None = None) -> CalibrationProfile:
        with SessionLocal() as db:
            item = CalibrationProfile(name=name, participant_id=participant_id,
                                      configuration_hash=configuration_hash,
                                      configuration_json=configuration_json,
                                      results_json=results_json,
                                      manual_checks_json=manual_checks_json, notes=notes,
                                      profile_type=profile_type, created_by_user_id=created_by_user_id)
            db.add(item); db.commit(); db.refresh(item); db.expunge(item)
            return item

    def list_calibration_profiles(self, participant_id: int | None = None) -> list[CalibrationProfile]:
        with SessionLocal() as db:
            query = select(CalibrationProfile).order_by(CalibrationProfile.id.desc())
            if participant_id is not None:
                query = query.where((CalibrationProfile.participant_id == participant_id) |
                                    (CalibrationProfile.participant_id.is_(None)))
            return list(db.scalars(query))

    def get_calibration_profile(self, profile_id: int) -> CalibrationProfile | None:
        with SessionLocal() as db:
            item = db.get(CalibrationProfile, profile_id)
            if item: db.expunge(item)
            return item

    def accept_calibration_profile(self, profile_id: int) -> CalibrationProfile:
        with SessionLocal() as db:
            item = db.get(CalibrationProfile, profile_id)
            if item is None: raise LookupError("Calibration profile not found")
            item.status = "accepted"; item.accepted_at = datetime.now(timezone.utc)
            db.commit(); db.refresh(item); db.expunge(item)
            return item

    def latest_accepted_calibration(self, participant_id: int | None = None) -> CalibrationProfile | None:
        with SessionLocal() as db:
            query = select(CalibrationProfile).where(CalibrationProfile.status == "accepted")
            if participant_id is not None:
                query = query.where((CalibrationProfile.participant_id == participant_id) |
                                    (CalibrationProfile.participant_id.is_(None)))
            item = db.scalar(query.order_by(CalibrationProfile.accepted_at.desc(), CalibrationProfile.id.desc()).limit(1))
            if item: db.expunge(item)
            return item

    def latest_accepted_calibration_type(self, profile_type: str,
                                         participant_id: int | None = None) -> CalibrationProfile | None:
        with SessionLocal() as db:
            query = select(CalibrationProfile).where(
                CalibrationProfile.status == "accepted",
                CalibrationProfile.profile_type == profile_type)
            if participant_id is not None:
                query = query.where(CalibrationProfile.participant_id == participant_id)
            elif profile_type == "system":
                query = query.where(CalibrationProfile.participant_id.is_(None))
            item = db.scalar(query.order_by(CalibrationProfile.accepted_at.desc(),
                                            CalibrationProfile.id.desc()).limit(1))
            if item: db.expunge(item)
            return item

    def create_calibration_verification(self, *, participant_id: int, calibration_profile_id: int,
                                        operator_id: int | None, passed: bool,
                                        checks_json: str) -> CalibrationVerification:
        with SessionLocal() as db:
            item = CalibrationVerification(participant_id=participant_id,
                                           calibration_profile_id=calibration_profile_id,
                                           operator_id=operator_id, passed=passed,
                                           checks_json=checks_json)
            db.add(item); db.commit(); db.refresh(item); db.expunge(item)
            return item

    def latest_passing_verification(self, participant_id: int,
                                    operator_id: int | None = None) -> CalibrationVerification | None:
        with SessionLocal() as db:
            query = select(CalibrationVerification).where(
                CalibrationVerification.participant_id == participant_id,
                CalibrationVerification.passed.is_(True))
            if operator_id is not None:
                query = query.where(CalibrationVerification.operator_id == operator_id)
            item = db.scalar(query.order_by(CalibrationVerification.created_at.desc()).limit(1))
            if item: db.expunge(item)
            return item

    def delete_calibration_profile(self, profile_id: int) -> None:
        with SessionLocal() as db:
            item = db.get(CalibrationProfile, profile_id)
            if item is None: raise LookupError("Calibration profile not found")
            if item.status == "accepted":
                raise RecordDeleteConflict("Accepted calibration profiles are immutable; create a replacement profile")
            db.delete(item); db.commit()

    def delete_session(self, session_id: int) -> None:
        with SessionLocal() as db:
            session = db.get(MonitoringSession, session_id)
            if session is None:
                raise LookupError("Session not found")
            if session.status == "active":
                raise RecordDeleteConflict("Stop the active session before deleting it")
            db.execute(delete(ResearchTaskTrial).where(ResearchTaskTrial.session_id == session_id))
            db.execute(delete(ResearchTaskRun).where(ResearchTaskRun.session_id == session_id))
            for model in (AttentionTrial, BlinkEvent, HeadPoseSample, HeadMovementEvent,
                          BodyMovementSample, BodyMovementEvent, PostureEvent,
                          TrackingValiditySample, SessionPhaseEvent, SessionSummary):
                db.execute(delete(model).where(model.session_id == session_id))
            db.execute(delete(AttentionTaskRun).where(AttentionTaskRun.session_id == session_id))
            db.delete(session)
            db.commit()

    def delete_participant(self, participant_id: int) -> None:
        with SessionLocal() as db:
            participant = db.get(Participant, participant_id)
            if participant is None:
                raise LookupError("Participant not found")
            has_session = db.scalar(select(MonitoringSession.id).where(
                MonitoringSession.participant_id == participant_id).limit(1))
            if has_session is not None:
                raise RecordDeleteConflict("Delete this participant's sessions first")
            db.delete(participant)
            db.commit()

    def add_audit_event(self, action: str, subject: str | None, client_ip: str | None,
                        success: bool = True, details: str | None = None) -> None:
        with SessionLocal() as db:
            db.add(AuditEvent(action=action, subject=subject, client_ip=client_ip,
                              success=success, details=details))
            db.commit()

    def list_audit_events(self, limit: int = 100) -> list[AuditEvent]:
        with SessionLocal() as db:
            return list(db.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit)))

    def list_participants(self, owner_user_id: int | None = None) -> list[Participant]:
        with SessionLocal() as db:
            query = select(Participant).order_by(Participant.participant_code)
            if owner_user_id is not None:
                query = query.where(Participant.created_by_user_id == owner_user_id)
            return list(db.scalars(query))

    def create_participant(self, code: str, display_name: str | None, age_group: str | None,
                           **details) -> Participant:
        participant = Participant(participant_code=code, display_name=display_name,
                                  age_group=age_group, **details)
        with SessionLocal() as db:
            db.add(participant)
            try:
                db.commit()
            except IntegrityError as exc:
                db.rollback()
                raise DuplicateParticipantCode(code) from exc
            db.refresh(participant)
            db.expunge(participant)
        return participant

    def update_participant(self, participant_id: int, **values) -> Participant:
        with SessionLocal() as db:
            item = db.get(Participant, participant_id)
            if item is None:
                raise LookupError("Participant not found")
            for key, value in values.items():
                if hasattr(item, key):
                    setattr(item, key, value)
            db.commit(); db.refresh(item); db.expunge(item)
            return item

    def list_user_accounts(self) -> list[UserAccount]:
        with SessionLocal() as db:
            return list(db.scalars(select(UserAccount).order_by(UserAccount.full_name)))

    def get_user_account(self, user_id: int) -> UserAccount | None:
        with SessionLocal() as db:
            item = db.get(UserAccount, user_id)
            if item: db.expunge(item)
            return item

    def find_user_by_token_hash(self, token_hash: str) -> UserAccount | None:
        with SessionLocal() as db:
            item = db.scalar(select(UserAccount).where(UserAccount.token_hash == token_hash))
            if item: db.expunge(item)
            return item

    def create_user_account(self, *, full_name: str, organization: str | None,
                            professional_title: str | None, role: str, token_hash: str,
                            token_hint: str, expires_at: datetime | None,
                            access_pin: str | None = None) -> UserAccount:
        with SessionLocal() as db:
            item = UserAccount(full_name=full_name, organization=organization,
                               professional_title=professional_title, role=role,
                               token_hash=token_hash, token_hint=token_hint, access_pin=access_pin,
                               expires_at=expires_at)
            db.add(item); db.commit(); db.refresh(item); db.expunge(item)
            return item

    def replace_user_token(self, user_id: int, *, token_hash: str,
                           token_hint: str, access_pin: str) -> UserAccount:
        with SessionLocal() as db:
            item = db.get(UserAccount, user_id)
            if item is None: raise LookupError("User account not found")
            item.token_hash = token_hash; item.token_hint = token_hint
            item.access_pin = access_pin; item.active = True
            db.commit(); db.refresh(item); db.expunge(item)
            return item

    def set_user_active(self, user_id: int, active: bool) -> UserAccount:
        with SessionLocal() as db:
            item = db.get(UserAccount, user_id)
            if item is None: raise LookupError("User account not found")
            item.active = active; db.commit(); db.refresh(item); db.expunge(item)
            return item

    def delete_user_account(self, user_id: int) -> None:
        with SessionLocal() as db:
            item = db.get(UserAccount, user_id)
            if item is None:
                raise LookupError("User account not found")
            participant = db.scalar(select(Participant.id).where(
                Participant.created_by_user_id == user_id).limit(1))
            session = db.scalar(select(MonitoringSession.id).where(
                MonitoringSession.operator_id == user_id).limit(1))
            calibration = db.scalar(select(CalibrationProfile.id).where(
                CalibrationProfile.created_by_user_id == user_id).limit(1))
            verification = db.scalar(select(CalibrationVerification.id).where(
                CalibrationVerification.operator_id == user_id).limit(1))
            if any(value is not None for value in (participant, session, calibration, verification)):
                raise RecordDeleteConflict(
                    "This account owns participant, session, or calibration records. Revoke it instead to preserve the audit history."
                )
            db.delete(item); db.commit()

    def record_user_login(self, user_id: int) -> None:
        with SessionLocal() as db:
            item = db.get(UserAccount, user_id)
            if item:
                item.last_login_at = datetime.now(timezone.utc); db.commit()

    def get_participant(self, participant_id: int) -> Participant | None:
        with SessionLocal() as db:
            item = db.get(Participant, participant_id)
            if item:
                db.expunge(item)
            return item

    def list_sessions(self, participant_id: int | None = None,
                      operator_id: int | None = None) -> list[MonitoringSession]:
        with SessionLocal() as db:
            query = select(MonitoringSession).order_by(MonitoringSession.start_time.desc())
            if participant_id is not None:
                query = query.where(MonitoringSession.participant_id == participant_id)
            if operator_id is not None:
                query = query.where(MonitoringSession.operator_id == operator_id)
            return list(db.scalars(query))

    def get_session(self, session_id: int) -> MonitoringSession | None:
        with SessionLocal() as db:
            item = db.get(MonitoringSession, session_id)
            if item:
                db.expunge(item)
            return item

    def get_summary(self, session_id: int) -> SessionSummary | None:
        with SessionLocal() as db:
            item = db.scalar(select(SessionSummary).where(SessionSummary.session_id == session_id))
            if item:
                db.expunge(item)
            return item

    def build_report(self, session_id: int) -> dict[str, object] | None:
        with SessionLocal() as db:
            session = db.get(MonitoringSession, session_id)
            if session is None:
                return None
            participant = db.get(Participant, session.participant_id)
            summary = db.scalar(select(SessionSummary).where(SessionSummary.session_id == session_id))
            def rows(model):
                return list(db.scalars(select(model).where(model.session_id == session_id).order_by(model.id)))
            blinks = rows(BlinkEvent)
            head_samples = rows(HeadPoseSample)
            head_events = rows(HeadMovementEvent)
            body_samples = rows(BodyMovementSample)
            body_events = rows(BodyMovementEvent)
            posture_events = rows(PostureEvent)
            trials = rows(AttentionTrial)
            attention_runs = rows(AttentionTaskRun)
            research_runs = rows(ResearchTaskRun)
            research_trials = rows(ResearchTaskTrial)
            validity_samples = rows(TrackingValiditySample)
            phase_events = rows(SessionPhaseEvent)
            operator = db.get(UserAccount, session.operator_id) if session.operator_id else None
            reaction_times = [item.reaction_time_ms for item in trials if item.reaction_time_ms is not None and item.is_target]
            completed = [item for item in trials if item.correct or item.incorrect or item.missed]
            correct = sum(item.correct for item in completed)
            duration = summary.duration_seconds if summary else (
                (session.end_time - session.start_time).total_seconds() if session.end_time else None
            )
            rt_mean = round(sum(reaction_times) / len(reaction_times), 1) if reaction_times else None
            rt_sd = round(statistics.pstdev(reaction_times), 1) if len(reaction_times) > 1 else None
            recorded_research = [item for item in research_trials if item.phase == "recorded"]
            valid_research = [item for item in recorded_research if item.valid]
            research_by_type = {}
            for task_type in ("fixation", "prosaccade", "antisaccade"):
                family = [item for item in recorded_research if item.task_type == task_type]
                valid = [item for item in family if item.valid]
                correct_items = [item for item in valid if item.correct is not None]
                latencies = [item.response_latency_ms for item in valid if item.response_latency_ms is not None]
                research_by_type[task_type] = {
                    "recorded": len(family), "valid": len(valid),
                    "invalid": len(family) - len(valid),
                    "correct": sum(bool(item.correct) for item in correct_items),
                    "accuracy": round(sum(bool(item.correct) for item in correct_items) * 100 / len(correct_items), 1)
                    if correct_items else None,
                    "average_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
                }
            head_valid_count = sum(bool(item.head_valid) for item in validity_samples)
            head_valid_pct = round(head_valid_count * 100 / len(validity_samples), 1) if validity_samples else 0.0
            body_valid_pct = round(sum(bool(item.body_valid) for item in validity_samples) * 100 /
                                   len(validity_samples), 1) if validity_samples else 0.0
            blink_valid_pct = round(sum(bool(item.eyes_valid) for item in validity_samples) * 100 /
                                    len(validity_samples), 1) if validity_samples else None
            attention_valid_pct = round(len(completed) * 100 / len(trials), 1) if trials else 0.0
            signal_valid_pct = {
                "head": head_valid_pct,
                "body": body_valid_pct,
                "attention": attention_valid_pct,
                "blink": blink_valid_pct,
            }
            quality_warnings = []
            for signal, valid_pct in signal_valid_pct.items():
                if valid_pct is not None and valid_pct < 80:
                    quality_warnings.append(f"{signal.title()}: only {valid_pct:.1f}% valid samples.")
            if not blinks and blink_valid_pct is not None and blink_valid_pct >= 80:
                quality_warnings.append("No blink events were observed despite adequate eye-tracking validity; this is a measured zero, not missing data.")
            elif not blinks and blink_valid_pct is None:
                quality_warnings.append("No validity samples are available, so zero blinks cannot be distinguished from missing eye tracking.")
            if recorded_research and len(valid_research) < max(1, round(len(recorded_research) * .8)):
                quality_warnings.append("Fewer than 80% of recorded eye-control trials were valid.")
            gaze_validated = any(item.gaze_validated for item in research_runs)
            if research_runs and not gaze_validated:
                quality_warnings.append("Screen-coordinate gaze was not validated; fixation and saccade outputs are unavailable.")
            participant_value = {
                "id": participant.id if participant else None,
                "code": participant.participant_code if participant else "UNKNOWN",
                "full_name": participant.display_name if participant else None,
                "date_of_birth": participant.date_of_birth if participant else None,
                "age_group": participant.age_group if participant else None,
                "sex": participant.sex if participant else None,
                "gender": participant.gender if participant else None,
                "grade_level": participant.grade_level if participant else None,
                "school_site": participant.school_site if participant else None,
                "address": participant.address if participant else None,
                "guardian_name": participant.guardian_name if participant else None,
                "consent_reference": participant.consent_reference if participant else None,
                "consent_date": participant.consent_date if participant else None,
                "diagnosis_status": participant.diagnosis_status if participant else None,
                "medication_notes": participant.medication_notes if participant else None,
                "accommodations": participant.accommodations if participant else None,
                "research_notes": participant.research_notes if participant else None,
            }
            quality_status = ("unusable" if any(value is not None and value < 50
                                                 for value in signal_valid_pct.values()) else
                              "usable_with_warnings" if quality_warnings else "usable")
            event_blink_rate = round(len(blinks) * 60 / duration, 1) if duration and duration > 0 else 0
            report = {
                "participant": participant_value,
                "session": {"id": session.id, "participant_id": session.participant_id,
                            "participant_code": participant.participant_code if participant else "UNKNOWN",
                            "start_time": session.start_time.isoformat(),
                            "end_time": session.end_time.isoformat() if session.end_time else None,
                            "duration_seconds": duration, "status": session.status, "mode": session.mode,
                            "notes": session.notes,
                            "operator": {"id": operator.id, "name": operator.full_name,
                                         "title": operator.professional_title,
                                         "organization": operator.organization} if operator else None},
                "blink": {"total": len(blinks),
                          "average_rate": event_blink_rate,
                          "events": [{"time": item.session_seconds, "ear": item.average_ear,
                                      "closure_duration_seconds": item.closure_duration_seconds,
                                      "phase": item.phase} for item in blinks]},
                "head": {"movement_count": len(head_events),
                         "samples": [{"time": item.session_seconds, "yaw": item.yaw,
                                      "pitch": item.pitch, "roll": item.roll, "valid": item.valid,
                                      "status": item.status, "phase": item.phase} for item in head_samples],
                         "events": [{"time": item.session_seconds, "direction": item.direction,
                                     "magnitude": item.magnitude, "phase": item.phase} for item in head_events]},
                "body": {"movement_events": len(body_events),
                         "posture_changes": len(posture_events),
                         "samples": [{"time": item.session_seconds, "magnitude": item.magnitude,
                                      "valid": item.valid, "status": item.status, "phase": item.phase}
                                     for item in body_samples],
                         "events": [{"time": item.session_seconds, "magnitude": item.magnitude,
                                     "phase": item.phase}
                                    for item in body_events],
                         "posture_events": [{"time": item.session_seconds, "angle": item.posture_angle,
                                             "phase": item.phase}
                                            for item in posture_events]},
                "attention": {"total_trials": len(completed), "correct": correct,
                              "incorrect": sum(item.incorrect for item in completed),
                              "missed": sum(item.missed for item in completed),
                              "false_responses": sum(item.false_response for item in completed),
                              "accuracy": round(correct * 100 / len(completed), 1) if completed else 0,
                              "average_reaction_time_ms": rt_mean,
                              "reaction_time_sd_ms": rt_sd,
                              "reaction_times": reaction_times,
                              "trials": [{"trial": item.trial_number, "stimulus": item.stimulus,
                                          "time": item.stimulus_session_seconds,
                                          "reaction_time_ms": item.reaction_time_ms,
                                          "is_target": item.is_target, "responded": item.responded,
                                          "correct": item.correct, "missed": item.missed,
                                          "false_response": item.false_response} for item in trials]},
                "attention_configuration": [{"id": item.id, "task_key": item.task_key,
                    "task_version": item.task_version, "age_profile": item.age_profile,
                    "difficulty": item.difficulty, "status": item.status,
                    "configuration": json.loads(item.configuration_json),
                    "started_at": item.started_at.isoformat(),
                    "completed_at": item.completed_at.isoformat() if item.completed_at else None}
                    for item in attention_runs],
                "research_tasks": {
                    "runs": [{"id": item.id, "protocol_key": item.protocol_key,
                              "protocol_version": item.protocol_version, "status": item.status,
                              "random_seed": item.random_seed, "gaze_provider": item.gaze_provider,
                              "gaze_validated": item.gaze_validated,
                              "started_at": item.started_at.isoformat(),
                              "configuration": json.loads(item.configuration_json),
                              "completed_at": item.completed_at.isoformat() if item.completed_at else None}
                             for item in research_runs],
                    "trials": [{"id": item.id, "run_id": item.run_id,
                                "sequence_number": item.sequence_number, "phase": item.phase,
                                "task_type": item.task_type, "target_direction": item.target_direction,
                                "expected_direction": item.expected_direction,
                                "observed_direction": item.observed_direction, "valid": item.valid,
                                "correct": item.correct, "invalid_reason": item.invalid_reason,
                                "response_latency_ms": item.response_latency_ms}
                               for item in research_trials],
                    "summary_by_type": research_by_type,
                    "recorded_total": len(recorded_research), "recorded_valid": len(valid_research),
                    "gaze_validated": gaze_validated,
                },
                "data_quality": {
                    "status": quality_status,
                    "warnings": quality_warnings,
                    "head_sample_count": len(head_samples), "body_sample_count": len(body_samples),
                    "blink_event_count": len(blinks), "attention_completed_count": len(completed),
                    "valid_pct": signal_valid_pct,
                    "research_recorded_count": len(recorded_research),
                    "research_valid_count": len(valid_research),
                    "validity_samples": [{"time": item.session_seconds, "phase": item.phase,
                        "face_valid": item.face_valid, "eyes_valid": item.eyes_valid,
                        "head_valid": item.head_valid, "body_valid": item.body_valid,
                        "face_status": item.face_status, "body_status": item.body_status}
                        for item in validity_samples],
                },
                "phases": [{"time": item.session_seconds, "phase": item.phase,
                            "occurred_at": item.occurred_at.isoformat()} for item in phase_events],
                "interpretation": {
                    "type": "descriptive_research_summary",
                    "measurement_families": [
                        {"key": "task", "label": "Task performance",
                         "observed": f"{correct}/{len(completed)} correct; {sum(item.missed for item in completed)} missed; mean response {rt_mean if rt_mean is not None else 'not available'} ms.",
                         "construct": "Sustained attention and response consistency", "diagnostic": False},
                        {"key": "blink", "label": "Blink / eye closure",
                         "observed": f"{len(blinks)} blinks; average rate {event_blink_rate}/min.",
                         "construct": "Observed blink behavior only", "diagnostic": False},
                        {"key": "head", "label": "Head movement",
                         "observed": f"{len(head_events)} calibrated head-movement events.",
                         "construct": "Observed movement during the session", "diagnostic": False},
                        {"key": "body", "label": "Body movement / posture",
                         "observed": f"{len(body_events)} movement events and {len(posture_events)} posture changes.",
                         "construct": "Restlessness-related observation; not validated by the cited eye studies", "diagnostic": False},
                        {"key": "gaze", "label": "Fixation and saccades",
                         "observed": "Reported by task type." if gaze_validated else "Not available — gaze model not validated.",
                         "construct": "Visual persistence, orienting, and inhibitory control", "diagnostic": False},
                    ],
                    "statement": "Results are descriptive observations for qualified review. No combined ADHD score or diagnostic classification is generated.",
                },
                "research_basis": [
                    {"short": "Chen et al. (2023)", "title": "Utilizing artificial intelligence-based eye tracking technology for screening ADHD symptoms in children", "doi": "10.3389/fpsyt.2023.1260031", "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10682190/", "use": "Fixation, prosaccade, antisaccade, task validity, and measurement-family definitions."},
                    {"short": "Merzon et al. (2022)", "title": "Eye movement behavior in a real-world virtual reality task reveals ADHD in children", "doi": "10.1038/s41598-022-24552-4", "url": "https://www.nature.com/articles/s41598-022-24552-4", "use": "Naturalistic multi-step task concepts and whole-session performance measures; this system is not EPELI or VR."},
                    {"short": "Perkins (2025)", "title": "Role of Eye-Tracking Technology and Software Algorithms in Enhancing ADHD Detection and Diagnosis: A Systematic Literature Review", "doi": None, "url": "https://digitalcommons.georgiasouthern.edu/honors-theses/1042/", "use": "Organization of candidate eye-feature families and limitations; not a local diagnostic validation source."},
                ],
                "disclaimer": "These measurements describe observed behavioral and task-performance signals and are not, by themselves, a diagnosis of ADHD.",
            }
            report["research_screening"] = screening_summary(report)
            return report


repository = Repository()
