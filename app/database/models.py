"""Phase 1 participant and monitoring-session models."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(primary_key=True)
    participant_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    age_group: Mapped[str | None] = mapped_column(String(40), nullable=True)
    date_of_birth: Mapped[str | None] = mapped_column(String(10), nullable=True)
    sex: Mapped[str | None] = mapped_column(String(30), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(50), nullable=True)
    grade_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    school_site: Mapped[str | None] = mapped_column(String(120), nullable=True)
    address: Mapped[str | None] = mapped_column(String(240), nullable=True)
    guardian_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    consent_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    consent_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    diagnosis_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    medication_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    accommodations: Mapped[str | None] = mapped_column(Text, nullable=True)
    research_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("user_accounts.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    sessions: Mapped[list["MonitoringSession"]] = relationship(back_populates="participant")


class ShapeMatchingRun(Base):
    """Separate durable shape records; never mixed with balloon trials."""
    __tablename__ = "shape_matching_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="waiting")
    plan_json: Mapped[str] = mapped_column(Text)
    rows_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class MonitoringSession(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id"), index=True)
    mode: Mapped[str] = mapped_column(String(20), default="real")
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("user_accounts.id"), nullable=True, index=True)
    participant: Mapped[Participant] = relationship(back_populates="sessions")


class BlinkEvent(Base):
    __tablename__ = "blink_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    session_seconds: Mapped[float] = mapped_column(Float)
    average_ear: Mapped[float | None] = mapped_column(Float, nullable=True)
    closure_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    phase: Mapped[str] = mapped_column(String(20), default="baseline", index=True)


class HeadPoseSample(Base):
    __tablename__ = "head_pose_samples"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    sampled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    session_seconds: Mapped[float] = mapped_column(Float)
    yaw: Mapped[float | None] = mapped_column(Float, nullable=True)
    pitch: Mapped[float | None] = mapped_column(Float, nullable=True)
    roll: Mapped[float | None] = mapped_column(Float, nullable=True)
    valid: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    phase: Mapped[str] = mapped_column(String(20), default="baseline", index=True)


class HeadMovementEvent(Base):
    __tablename__ = "head_movement_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    session_seconds: Mapped[float] = mapped_column(Float)
    direction: Mapped[str] = mapped_column(String(20))
    magnitude: Mapped[float] = mapped_column(Float)
    phase: Mapped[str] = mapped_column(String(20), default="baseline", index=True)


class BodyMovementSample(Base):
    __tablename__ = "body_movement_samples"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    sampled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    session_seconds: Mapped[float] = mapped_column(Float)
    magnitude: Mapped[float] = mapped_column(Float)
    regional_json: Mapped[str] = mapped_column(Text, default="{}")
    valid: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    phase: Mapped[str] = mapped_column(String(20), default="baseline", index=True)


class BodyMovementEvent(Base):
    __tablename__ = "body_movement_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    session_seconds: Mapped[float] = mapped_column(Float)
    magnitude: Mapped[float] = mapped_column(Float)
    phase: Mapped[str] = mapped_column(String(20), default="baseline", index=True)


class PostureEvent(Base):
    __tablename__ = "posture_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    session_seconds: Mapped[float] = mapped_column(Float)
    posture_angle: Mapped[float | None] = mapped_column(Float, nullable=True)
    phase: Mapped[str] = mapped_column(String(20), default="baseline", index=True)


class TrackingValiditySample(Base):
    """One periodic validity row, including lost tracking and zero-event periods."""

    __tablename__ = "tracking_validity_samples"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    sampled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    session_seconds: Mapped[float] = mapped_column(Float)
    phase: Mapped[str] = mapped_column(String(20), default="baseline", index=True)
    face_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    eyes_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    head_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    body_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    face_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    body_status: Mapped[str | None] = mapped_column(String(40), nullable=True)


class SessionPhaseEvent(Base):
    __tablename__ = "session_phase_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    session_seconds: Mapped[float] = mapped_column(Float)
    phase: Mapped[str] = mapped_column(String(20), index=True)


class SessionSummary(Base):
    __tablename__ = "session_summaries"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), unique=True, index=True)
    duration_seconds: Mapped[float] = mapped_column(Float)
    total_blinks: Mapped[int] = mapped_column(Integer, default=0)
    average_blink_rate: Mapped[float] = mapped_column(Float, default=0)
    head_movements: Mapped[int] = mapped_column(Integer, default=0)
    body_movement_events: Mapped[int] = mapped_column(Integer, default=0)
    posture_changes: Mapped[int] = mapped_column(Integer, default=0)
    mock_data: Mapped[bool] = mapped_column(Boolean, default=False)
    summary_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AttentionTrial(Base):
    __tablename__ = "attention_trials"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_run_id: Mapped[int | None] = mapped_column(ForeignKey("attention_task_runs.id"), nullable=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    trial_number: Mapped[int] = mapped_column(Integer)
    stimulus: Mapped[str] = mapped_column(String(30))
    stimulus_json: Mapped[str] = mapped_column(Text, default="{}")
    phase: Mapped[str] = mapped_column(String(20), default="recorded", index=True)
    is_target: Mapped[bool] = mapped_column(Boolean)
    stimulus_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    stimulus_session_seconds: Mapped[float] = mapped_column(Float)
    response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response_session_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    reaction_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    responded: Mapped[bool] = mapped_column(Boolean, default=False)
    correct: Mapped[bool] = mapped_column(Boolean, default=False)
    incorrect: Mapped[bool] = mapped_column(Boolean, default=False)
    missed: Mapped[bool] = mapped_column(Boolean, default=False)
    false_response: Mapped[bool] = mapped_column(Boolean, default=False)
    premature_taps: Mapped[int] = mapped_column(Integer, default=0)


class AttentionTaskRun(Base):
    """Versioned participant-screen configuration attached to one session."""
    __tablename__ = "attention_task_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id"), index=True)
    task_key: Mapped[str] = mapped_column(String(50), index=True)
    task_version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    age_profile: Mapped[str] = mapped_column(String(20), index=True)
    difficulty: Mapped[str] = mapped_column(String(20), index=True)
    configuration_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    termination_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ResearchTaskRun(Base):
    """Immutable protocol snapshot attached to a monitoring session."""

    __tablename__ = "research_task_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    protocol_key: Mapped[str] = mapped_column(String(80), index=True)
    protocol_version: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    random_seed: Mapped[int] = mapped_column(Integer)
    configuration_json: Mapped[str] = mapped_column(Text)
    gaze_provider: Mapped[str] = mapped_column(String(80), default="unavailable")
    gaze_validated: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    aborted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ResearchTaskTrial(Base):
    """One planned practice or recorded trial in a versioned research run."""

    __tablename__ = "research_task_trials"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("research_task_runs.id"), index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    sequence_number: Mapped[int] = mapped_column(Integer)
    phase: Mapped[str] = mapped_column(String(20), index=True)
    task_type: Mapped[str] = mapped_column(String(30), index=True)
    cue: Mapped[str] = mapped_column(String(30))
    target_direction: Mapped[str | None] = mapped_column(String(10), nullable=True)
    expected_direction: Mapped[str | None] = mapped_column(String(10), nullable=True)
    requires_gaze: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="planned", index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    client_started_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    client_completed_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    observed_direction: Mapped[str | None] = mapped_column(String(10), nullable=True)
    response_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    valid: Mapped[bool] = mapped_column(Boolean, default=False)
    correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    invalid_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    subject: Mapped[str | None] = mapped_column(String(120), nullable=True)
    client_ip: Mapped[str | None] = mapped_column(String(80), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)


class UserAccount(Base):
    """Named local operator account authenticated by a revocable access token."""

    __tablename__ = "user_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), index=True)
    organization: Mapped[str | None] = mapped_column(String(160), nullable=True)
    professional_title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="operator", index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    token_hint: Mapped[str] = mapped_column(String(12))
    access_pin: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CalibrationProfile(Base):
    """Versioned, reviewable snapshot of a physical/measurement calibration."""

    __tablename__ = "calibration_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    participant_id: Mapped[int | None] = mapped_column(ForeignKey("participants.id"), nullable=True, index=True)
    profile_type: Mapped[str] = mapped_column(String(20), default="participant", index=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("user_accounts.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    schema_version: Mapped[str] = mapped_column(String(20), default="calibration-1.0")
    configuration_hash: Mapped[str] = mapped_column(String(64), index=True)
    configuration_json: Mapped[str] = mapped_column(Text)
    results_json: Mapped[str] = mapped_column(Text)
    manual_checks_json: Mapped[str] = mapped_column(Text, default="{}")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CalibrationVerification(Base):
    """Short, per-session readiness check; not a replacement for a baseline."""

    __tablename__ = "calibration_verifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id"), index=True)
    calibration_profile_id: Mapped[int] = mapped_column(ForeignKey("calibration_profiles.id"), index=True)
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("user_accounts.id"), nullable=True, index=True)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    checks_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class SystemSetupState(Base):
    """Durable installation-wide first-run setup and repair state."""

    __tablename__ = "system_setup_state"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    status: Mapped[str] = mapped_column(String(24), default="setup_required", index=True)
    current_step: Mapped[int] = mapped_column(Integer, default=1)
    progress_json: Mapped[str] = mapped_column(Text, default="{}")
    configuration_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    calibration_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    completed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("user_accounts.id"), nullable=True)
    completed_by_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
