"""Phase 1 REST endpoints."""

import json
import importlib.metadata
import os
import socket
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, Request, Response, UploadFile, File, Form
from pydantic import BaseModel, ConfigDict, Field, field_validator
import psutil
import torch
import httpx
import qrcode
import qrcode.image.svg

from app.camera.camera_manager import discover_usb_cameras
from app.camera.camera_system import camera_system
from app.config import settings
from app.services.mock_monitor import mock_monitor
from app.services.face_analysis_service import face_analysis_service
from app.services.body_analysis_service import body_analysis_service
from app.database.repository import DuplicateParticipantCode, RecordDeleteConflict, repository
from app.sessions.session_manager import SessionConflict, session_manager
from app.tasks.attention_task import AttentionTaskConflict, attention_task_service, task_catalog
from app.tasks import shape_matching
from app.tasks.research_protocols import (
    ResearchTaskConflict, protocol_catalog, research_task_service,
)
from app.services.settings_service import current_settings, save_settings
from app.services.hardware_validation import node_health_url, validation_report
from app.services.export_service import database_backup_archive, session_archive, session_json
from app.services.landmark_config import validate_selection
from app.services.calibration_service import (configuration_hash, create_profile,
                                              check_allowed,
                                              payload as calibration_payload,
                                              readiness as calibration_readiness)
from app.services.performance_health import evaluate_pipeline
from app.services.reference_data_service import status as reference_status, import_csv as import_reference_csv
from app.services.system_setup_service import (complete_setup, reset_setup, save_progress,
                                                record_direction_observation, invalidate_direction_progress,
                                                status_payload as setup_status_payload)
from app.services.access_control import (COOKIE_NAME, decrypt_recoverable_pin, encrypt_recoverable_pin,
                                         generate_access_token, token_hash, token_identity)


class ParticipantCreate(BaseModel):
    participant_code: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    display_name: str | None = Field(default=None, max_length=120)
    age_group: str | None = Field(default=None, max_length=40)
    date_of_birth: str | None = Field(default=None, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$")
    sex: str | None = Field(default=None, max_length=30)
    gender: str | None = Field(default=None, max_length=50)
    grade_level: str | None = Field(default=None, max_length=50)
    school_site: str | None = Field(default=None, max_length=120)
    address: str | None = Field(default=None, max_length=240)
    guardian_name: str | None = Field(default=None, max_length=120)
    consent_reference: str | None = Field(default=None, max_length=120)
    consent_date: str | None = Field(default=None, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$")
    diagnosis_status: str | None = Field(default=None, pattern=r"^(not_provided|under_assessment|previously_diagnosed)$")
    medication_notes: str | None = Field(default=None, max_length=1000)
    accommodations: str | None = Field(default=None, max_length=1000)
    research_notes: str | None = Field(default=None, max_length=2000)

    @field_validator("participant_code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()


class ParticipantUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    age_group: str | None = Field(default=None, max_length=40)
    date_of_birth: str | None = Field(default=None, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$")
    sex: str | None = Field(default=None, max_length=30)
    gender: str | None = Field(default=None, max_length=50)
    grade_level: str | None = Field(default=None, max_length=50)
    school_site: str | None = Field(default=None, max_length=120)
    address: str | None = Field(default=None, max_length=240)
    guardian_name: str | None = Field(default=None, max_length=120)
    consent_reference: str | None = Field(default=None, max_length=120)
    consent_date: str | None = Field(default=None, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$")
    diagnosis_status: str | None = Field(default=None, pattern=r"^(not_provided|under_assessment|previously_diagnosed)$")
    medication_notes: str | None = Field(default=None, max_length=1000)
    accommodations: str | None = Field(default=None, max_length=1000)
    research_notes: str | None = Field(default=None, max_length=2000)


class UserAccountCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    organization: str | None = Field(default=None, max_length=160)
    professional_title: str | None = Field(default=None, max_length=100)
    role: str = Field(default="operator", pattern=r"^(admin|operator)$")
    expires_in_days: int | None = Field(default=30, ge=1, le=3650)


class SessionStart(BaseModel):
    participant_id: int = Field(gt=0)
    notes: str | None = Field(default=None, max_length=2000)
    model_config = {"extra": "forbid"}


class SessionStop(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)


class AttentionTaskStart(BaseModel):
    task_key: str = Field(default="pop_balloon", pattern=r"^pop_balloon$")
    age_profile: str = Field(default="child", pattern=r"^(child|preteen|teen|adult)$")
    difficulty: str = Field(default="easy", pattern=r"^(easy|moderate|hard|standard)$")
    required_pops: int = Field(default=20, ge=5, le=50)
    game_mode: str | None = Field(default=None, pattern=r"^(any|target_color)$")
    target_color: str = Field(default="sky", pattern=r"^(coral|sky|turquoise|yellow|purple|orange|green|pink)$")
    sound_enabled: bool = True
    maximum_duration_seconds: int = Field(default=300, ge=60, le=600)


class AttentionPracticeStart(BaseModel):
    task_key: str = Field(default="pop_balloon", pattern=r"^pop_balloon$")
    age_profile: str = Field(pattern=r"^(child|preteen|teen|adult)$")
    difficulty: str = Field(pattern=r"^(easy|moderate|hard|standard)$")
    required_pops: int = Field(default=20, ge=5, le=50)
    game_mode: str | None = Field(default=None, pattern=r"^(any|target_color)$")
    target_color: str = Field(default="sky", pattern=r"^(coral|sky|turquoise|yellow|purple|orange|green|pink)$")
    sound_enabled: bool = True
    maximum_duration_seconds: int = Field(default=300, ge=60, le=600)


class TrialComplete(BaseModel):
    responded: bool
    reaction_time_ms: float | None = Field(default=None, ge=0, le=10000)
    premature_taps: int = Field(default=0, ge=0, le=1000)


class AttentionAbort(BaseModel):
    reason: str = Field(default="operator_ended", min_length=1, max_length=80)


class ResearchTaskStart(BaseModel):
    protocol_key: str = Field(min_length=1, max_length=80)
    random_seed: int | None = Field(default=None, ge=0, le=2_147_483_647)
    gaze_provider: str = Field(default="unavailable", min_length=1, max_length=80)
    gaze_validated: bool = False


class ResearchTrialComplete(BaseModel):
    observed_direction: str | None = Field(default=None, pattern=r"^(left|right|center)$")
    response_latency_ms: float | None = Field(default=None, ge=0, le=60000)
    client_started_ms: float | None = Field(default=None, ge=0)
    client_completed_ms: float | None = Field(default=None, ge=0)
    tracking_valid: bool
    invalid_reason: str | None = Field(default=None, max_length=120)
    metrics: dict[str, object] = Field(default_factory=dict)


class SettingsUpdate(BaseModel):
    face_camera_source: str = Field(min_length=1, max_length=500)
    body_camera_source: str = Field(min_length=1, max_length=500)
    camera_width: int = Field(ge=320, le=3840)
    camera_height: int = Field(ge=240, le=2160)
    camera_fps: int = Field(ge=1, le=60)
    face_camera_width: int = Field(ge=320, le=3840)
    face_camera_height: int = Field(ge=240, le=2160)
    face_camera_fps: int = Field(ge=1, le=60)
    body_camera_width: int = Field(ge=320, le=3840)
    body_camera_height: int = Field(ge=240, le=2160)
    body_camera_fps: int = Field(ge=1, le=60)
    face_process_fps: int = Field(ge=1, le=30)
    body_process_fps: int = Field(ge=1, le=30)
    ear_threshold: float = Field(gt=0.05, lt=0.6)
    min_closed_frames: int = Field(ge=1, le=15)
    blink_refractory_seconds: float = Field(ge=0.05, le=2.0)
    head_pose_smoothing_alpha: float = Field(gt=0, le=1)
    head_movement_threshold_degrees: float = Field(ge=2, le=90)
    body_movement_threshold: float = Field(gt=0, le=1)
    posture_change_threshold_degrees: float = Field(ge=2, le=90)
    pose_confidence: float = Field(ge=0.1, le=0.95)
    keypoint_confidence: float = Field(ge=0.1, le=0.95)
    show_face_landmarks: bool
    show_body_skeleton: bool
    landmark_profile: str = Field(pattern=r"^(core_monitoring|upper_body|full_body|custom)$")
    face_display_groups: str = Field(max_length=200)
    face_measure_groups: str = Field(max_length=200)
    body_display_groups: str = Field(max_length=300)
    body_measure_groups: str = Field(max_length=300)
    feature_types: str = Field(max_length=300)
    save_raw_video: bool = False

    @field_validator("face_camera_source", "body_camera_source")
    @classmethod
    def safe_source(cls, value: str) -> str:
        cleaned = value.strip()
        if "\n" in cleaned or "\r" in cleaned:
            raise ValueError("Camera source cannot contain line breaks")
        return cleaned


class CalibrationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    participant_id: int | None = Field(default=None, gt=0)
    profile_type: str = Field(default="system", pattern=r"^system$")
    notes: str | None = Field(default=None, max_length=2000)
    manual_checks: dict[str, bool] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return value.strip()


class CalibrationVerificationCreate(BaseModel):
    participant_id: int = Field(gt=0)
    face_visible: bool
    distance_ok: bool
    body_visible: bool
    lighting_ok: bool


class SetupProgressUpdate(BaseModel):
    step: int = Field(ge=1, le=6)
    values: dict[str, object] = Field(default_factory=dict)


class SetupCompletionRequest(BaseModel):
    confirm: bool


class SetupDirectionCheck(BaseModel):
    expected: str = Field(pattern=r"^(UP|DOWN|LEFT|RIGHT|CENTER)$")


def participant_payload(item) -> dict[str, object]:
    fields = ("id", "participant_code", "display_name", "age_group", "date_of_birth", "sex", "gender",
              "grade_level", "school_site", "address", "guardian_name", "consent_reference", "consent_date",
              "diagnosis_status", "medication_notes", "accommodations", "research_notes", "created_by_user_id")
    result = {field: getattr(item, field) for field in fields}
    result["created_at"] = item.created_at.isoformat()
    return result


def user_payload(item) -> dict[str, object]:
    return {"id": item.id, "full_name": item.full_name, "organization": item.organization,
            "professional_title": item.professional_title, "role": item.role,
            "token_hint": item.token_hint, "access_token": decrypt_recoverable_pin(item.access_pin), "active": item.active,
            "expires_at": item.expires_at.isoformat() if item.expires_at else None,
            "created_at": item.created_at.isoformat(),
            "last_login_at": item.last_login_at.isoformat() if item.last_login_at else None}


def session_payload(item) -> dict[str, object]:
    return {"id": item.id, "participant_id": item.participant_id, "mode": item.mode, "status": item.status,
            "start_time": item.start_time.isoformat(),
            "end_time": item.end_time.isoformat() if item.end_time else None, "notes": item.notes,
            "operator_id": item.operator_id}

router = APIRouter(prefix="/api")
SERVER_STARTED = time.monotonic()


def _request_identity(request: Request):
    return token_identity(request.cookies.get(COOKIE_NAME))


def _require_setup_admin(request: Request):
    identity = _request_identity(request)
    if identity is not None and identity.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Owner or administrator access required")
    return identity


@router.get("/setup/status")
def get_setup_status() -> dict[str, object]:
    return setup_status_payload()


@router.put("/setup/progress")
def update_setup_progress(payload: SetupProgressUpdate, request: Request) -> dict[str, object]:
    identity = _require_setup_admin(request)
    result = save_progress(payload.step, payload.values)
    repository.add_audit_event("setup.progress", identity.full_name if identity else "local owner",
                               request.client.host if request.client else None, details=f"step={payload.step}")
    return result


@router.post("/setup/complete")
def finish_initial_setup(payload: SetupCompletionRequest, request: Request) -> dict[str, object]:
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Review and confirm the setup summary")
    identity = _require_setup_admin(request)
    try:
        result = complete_setup(identity.user_id if identity else None,
                                identity.full_name if identity else "Local owner")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    repository.add_audit_event("setup.complete", identity.full_name if identity else "local owner",
                               request.client.host if request.client else None)
    return result


@router.post("/setup/direction-check")
def check_setup_direction(payload: SetupDirectionCheck, request: Request) -> dict[str, object]:
    identity = _require_setup_admin(request)
    face = face_analysis_service.snapshot()
    if not settings.mock_mode and (not face.get("tracking") or not face.get("head_calibrated")):
        raise HTTPException(status_code=409, detail="Keep one calibrated face visible before checking directions")
    observed = payload.expected if settings.mock_mode else str(face.get("head_direction") or "").upper()
    try:
        result = record_direction_observation(payload.expected, observed)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    repository.add_audit_event("setup.direction", identity.full_name if identity else "local owner",
                               request.client.host if request.client else None,
                               details=f"expected={payload.expected}; observed={observed}")
    return {"expected": payload.expected, "observed": observed,
            "progress": result["progress"].get("step_5", {}), "setup": result}


@router.post("/setup/reset")
def reset_initial_setup(payload: SetupCompletionRequest, request: Request) -> dict[str, object]:
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required")
    identity = _require_setup_admin(request)
    result = reset_setup()
    repository.add_audit_event("setup.reset", identity.full_name if identity else "local owner",
                               request.client.host if request.client else None)
    return result


@router.get("/research-reference")
def get_research_reference(request: Request) -> dict[str, object]:
    _require_setup_admin(request)
    return reference_status()


@router.post("/research-reference/import")
async def import_research_reference(request: Request,
                                    file: UploadFile = File(...), version: str = Form(...),
                                    cohort: str = Form(...), source: str = Form(...),
                                    approval_reference: str = Form(...)) -> dict[str, object]:
    identity = _require_setup_admin(request)
    if file.content_type not in {"text/csv", "application/vnd.ms-excel", "application/octet-stream"}:
        raise HTTPException(status_code=422, detail="Upload a CSV reference file")
    content = await file.read()
    if len(content) > 5_000_000:
        raise HTTPException(status_code=413, detail="Reference CSV exceeds 5 MB")
    try:
        result = import_reference_csv(content, version=version, cohort=cohort, source=source,
                                      approval_reference=approval_reference,
                                      imported_by=identity.full_name if identity else "Local owner")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    repository.add_audit_event("research_reference.import", file.filename,
                               request.client.host if request.client else None,
                               details=f"version={version}; rows={result['rows']}")
    return result


def _require_participant_access(request: Request, participant_id: int) -> None:
    item = repository.get_participant(participant_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Participant not found")
    identity = _request_identity(request)
    if identity and identity.role in {"operator", "reviewer"} and item.created_by_user_id != identity.user_id:
        raise HTTPException(status_code=403, detail="This participant is not assigned to your account")


def _require_session_access(request: Request, session_id: int) -> None:
    item = repository.get_session(session_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Session not found")
    identity = _request_identity(request)
    if identity and identity.role in {"operator", "reviewer"} and item.operator_id != identity.user_id:
        raise HTTPException(status_code=403, detail="This session is not assigned to your account")


def _require_active_task_access(request: Request) -> None:
    """Shared task controls must not act on another operator's session."""
    session_id = session_manager.active_session_id
    if session_id is not None:
        _require_session_access(request, session_id)


def _require_calibration_access(request: Request, item) -> None:
    identity = _request_identity(request)
    if identity and identity.role in {"operator", "reviewer"}:
        if item.profile_type == "system":
            return  # Operators may inspect the shared room setup.
        if item.participant_id is None:
            raise HTTPException(status_code=403, detail="Calibration is not assigned to your account")
        _require_participant_access(request, item.participant_id)


@router.get("/participants")
def list_participants(request: Request) -> list[dict[str, object]]:
    identity = token_identity(request.cookies.get(COOKIE_NAME))
    owner_id = identity.user_id if identity and identity.role in {"operator", "reviewer"} else None
    return [participant_payload(item) for item in repository.list_participants(owner_id)]


@router.post("/participants", status_code=201)
def create_participant(payload: ParticipantCreate, request: Request) -> dict[str, object]:
    identity = token_identity(request.cookies.get(COOKIE_NAME))
    try:
        values = payload.model_dump(exclude={"participant_code", "display_name", "age_group"})
        values["created_by_user_id"] = identity.user_id if identity else None
        item = repository.create_participant(payload.participant_code, payload.display_name, payload.age_group, **values)
    except DuplicateParticipantCode:
        raise HTTPException(status_code=409, detail="Participant code already exists")
    repository.add_audit_event("participant.create", item.participant_code,
                               request.client.host if request.client else None)
    return participant_payload(item)


@router.put("/participants/{participant_id}")
def update_participant(participant_id: int, payload: ParticipantUpdate, request: Request) -> dict[str, object]:
    _require_participant_access(request, participant_id)
    try:
        item = repository.update_participant(participant_id, **payload.model_dump(exclude_unset=True))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    repository.add_audit_event("participant.update", item.participant_code,
                               request.client.host if request.client else None)
    return participant_payload(item)


@router.get("/auth/me")
def current_user(request: Request) -> dict[str, object]:
    identity = token_identity(request.cookies.get(COOKIE_NAME))
    if identity is None:
        return {"authenticated": not settings.auth_enabled, "full_name": "Local user", "role": "owner"}
    return {"authenticated": True, "user_id": identity.user_id,
            "full_name": identity.full_name, "role": identity.role}


@router.get("/users")
def list_users() -> list[dict[str, object]]:
    return [user_payload(item) for item in repository.list_user_accounts()]


@router.post("/users", status_code=201)
def create_user(payload: UserAccountCreate, request: Request) -> dict[str, object]:
    raw_token = generate_access_token()
    expiry = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days) if payload.expires_in_days else None
    item = repository.create_user_account(full_name=payload.full_name.strip(),
        organization=payload.organization, professional_title=payload.professional_title,
        role=payload.role, token_hash=token_hash(raw_token), token_hint=raw_token[-4:],
        access_pin=encrypt_recoverable_pin(raw_token), expires_at=expiry)
    repository.add_audit_event("user.create", item.full_name,
                               request.client.host if request.client else None, details=f"role={item.role}")
    result = user_payload(item); result["access_token"] = raw_token
    result["token_notice"] = "PIN encrypted at rest. Owner/Admin may view or replace it."
    return result


@router.post("/users/{user_id}/regenerate-token")
def regenerate_user_token(user_id: int, request: Request) -> dict[str, object]:
    raw_token = generate_access_token()
    try:
        item = repository.replace_user_token(user_id, token_hash=token_hash(raw_token),
                                             token_hint=raw_token[-4:], access_pin=encrypt_recoverable_pin(raw_token))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    repository.add_audit_event("user.token_regenerate", item.full_name,
                               request.client.host if request.client else None)
    result = user_payload(item)
    result["token_notice"] = "Previous token was replaced. Share this PIN privately."
    return result


@router.post("/users/{user_id}/status")
def set_user_status(user_id: int, request: Request, active: bool = Query(...)) -> dict[str, object]:
    try: item = repository.set_user_active(user_id, active)
    except LookupError as exc: raise HTTPException(status_code=404, detail=str(exc))
    repository.add_audit_event("user.status", item.full_name,
                               request.client.host if request.client else None, details=f"active={active}")
    return user_payload(item)


@router.delete("/users/{user_id}", status_code=204)
def delete_user_account(user_id: int, request: Request,
                        confirm: bool = Query(False)) -> Response:
    if not confirm:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required")
    identity = _request_identity(request)
    if identity and identity.user_id == user_id:
        raise HTTPException(status_code=409, detail="You cannot delete the account currently signed in")
    try:
        repository.delete_user_account(user_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RecordDeleteConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    repository.add_audit_event("user.delete", str(user_id),
                               request.client.host if request.client else None)
    return Response(status_code=204)


@router.delete("/participants/{participant_id}", status_code=204)
def delete_participant(participant_id: int, request: Request, confirm: bool = Query(False)) -> Response:
    if not confirm:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required")
    _require_participant_access(request, participant_id)
    try:
        repository.delete_participant(participant_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RecordDeleteConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    repository.add_audit_event("participant.delete", str(participant_id),
                               request.client.host if request.client else None)
    return Response(status_code=204)


@router.get("/sessions")
def list_sessions(request: Request, participant_id: int | None = Query(default=None, gt=0)) -> list[dict[str, object]]:
    identity = token_identity(request.cookies.get(COOKIE_NAME))
    operator_id = identity.user_id if identity and identity.role in {"operator", "reviewer"} else None
    return [session_payload(item) for item in repository.list_sessions(participant_id, operator_id)]


@router.get("/sessions/active")
def active_session(request: Request) -> dict[str, object]:
    session_id = session_manager.active_session_id
    session = repository.get_session(session_id) if session_id is not None else None
    if session is not None:
        _require_session_access(request, session.id)
    participant = repository.get_participant(session.participant_id) if session else None
    return {"active": session_id is not None, "session_id": session_id,
            "session_time": session_manager.elapsed(),
            "participant": participant_payload(participant) if participant else None}


@router.get("/workflow/status")
def workflow_status(request: Request,
                    participant_id: int | None = Query(default=None, gt=0)) -> dict[str, object]:
    """Return one operator-facing source of truth for the guided workflow."""
    session_id = session_manager.active_session_id
    session = repository.get_session(session_id) if session_id is not None else None
    if session is not None:
        _require_session_access(request, session.id)
        participant_id = session.participant_id
    participant = repository.get_participant(participant_id) if participant_id else None
    if participant_id is not None:
        _require_participant_access(request, participant_id)

    cameras = camera_system.status()
    connected_values = {"CONNECTED", "MOCK"}
    camera_ready = (
        cameras["face"]["status"] in connected_values
        and cameras["body"]["status"] in connected_values
        and not cameras.get("source_conflict", False)
    )
    calibration = get_calibration_status(request, participant_id)
    task = attention_task_service.public_status()
    task_phase = str(task.get("phase", "waiting"))

    steps = [
        {"id": "cameras", "label": "Cameras", "complete": camera_ready,
         "href": "/settings#camera-setup",
         "detail": ("Both camera inputs are ready." if camera_ready else
                    "Connect and assign separate face and body camera inputs.")},
        {"id": "room", "label": "Room setup", "complete": bool(calibration["system_ready"]),
         "href": "/calibration?mode=system",
         "detail": ("Room setup is accepted." if calibration["system_ready"] else
                    "Complete the owner/operator room check.")},
        {"id": "participant", "label": "Participant", "complete": participant is not None,
         "href": "/participants",
         "detail": (f"Selected: {participant.participant_code}" if participant else
                    "Select or create a participant.")},
        {"id": "session", "label": "Start session",
         "complete": session is not None,
         "href": "/",
         "detail": ("Monitoring session is active." if session else
                    "Start monitoring; cameras and framing are checked automatically.")},
        {"id": "activity", "label": "Activity",
         "complete": task_phase == "complete",
         "href": "/attention-task/operator",
         "detail": ("Recorded task completed." if task_phase == "complete" else
                    "Configure, practice, and run the participant activity.")},
        {"id": "results", "label": "Results", "complete": False,
         "href": "/records", "detail": "Stop the session to generate the final report."},
    ]

    if not camera_ready:
        current = "cameras"
    elif not calibration["system_ready"]:
        current = "room"
    elif participant is None:
        current = "participant"
    elif session is None:
        current = "session"
    elif task_phase != "complete":
        current = "activity"
    else:
        current = "results"

    current_step = next(item for item in steps if item["id"] == current)
    blockers: list[str] = []
    if cameras.get("source_conflict"):
        blockers.append("Face and body are assigned to the same camera source.")
    for name in ("face", "body"):
        status = cameras[name]
        if status["status"] not in connected_values:
            blockers.append(str(status.get("last_error") or f"{name.title()} camera is {status['status']}."))
    if current == "room" and not blockers:
        blockers.append(str(calibration["message"]))
    elif current == "session" and not blockers:
        blockers.append("Select Start session. The live camera check runs automatically.")

    return {
        "current_step": current,
        "next_action": {"label": current_step["label"], "href": current_step["href"]},
        "steps": steps,
        "blockers": list(dict.fromkeys(blockers)),
        "camera_ready": camera_ready,
        "calibration": calibration,
        "active_session": session_payload(session) if session else None,
        "participant": participant_payload(participant) if participant else None,
        "task": task,
    }


@router.post("/sessions/start", status_code=201)
def start_session(payload: SessionStart, request: Request) -> dict[str, object]:
    _require_participant_access(request, payload.participant_id)
    if repository.get_participant(payload.participant_id) is None:
        raise HTTPException(status_code=404, detail="Participant not found")
    if not settings.mock_mode:
        identity = _request_identity(request)
        system_profile = repository.latest_accepted_calibration_type("system")
        if system_profile is None:
            raise HTTPException(status_code=409, detail="Owner or device operator must complete and accept System / Room Calibration first")
        if system_profile.configuration_hash != configuration_hash():
            raise HTTPException(status_code=409, detail="Camera or analysis settings changed; accept a replacement room setup before recording")
        # Daily operation has no second manual calibration workflow. Sample the live
        # cameras quietly for two seconds, keep the result for the audit trail, and
        # return one focused operator action only when a required signal is missing.
        critical_order = (
            "face_camera", "body_camera", "face_tracking", "body_tracking",
            "face_fps", "body_fps", "privacy",
        )
        critical_ids = set(critical_order)
        sample_count = 5
        pass_counts = {identifier: 0 for identifier in critical_ids}
        latest_checks: dict[str, dict[str, object]] = {}
        for sample_index in range(sample_count):
            for check_item in calibration_readiness()["checks"]:
                identifier = str(check_item["id"])
                if identifier not in critical_ids:
                    continue
                latest_checks[identifier] = check_item
                if check_allowed(check_item):
                    pass_counts[identifier] += 1
            if sample_index < sample_count - 1:
                time.sleep(0.5)
        passed_ids = {identifier for identifier, count in pass_counts.items() if count >= 3}
        failed = [latest_checks[identifier] for identifier in critical_order
                  if identifier not in passed_ids and identifier in latest_checks]
        automatic_checks = {
            "automatic": True, "duration_seconds": 2.0,
            "samples": sample_count, "required_passes": 3,
            "results": {identifier: {
                "passed": identifier in passed_ids,
                "passing_samples": pass_counts[identifier],
                "detail": str(latest_checks.get(identifier, {}).get("detail", "Unavailable")),
            } for identifier in sorted(critical_ids)},
        }
        verification = repository.create_calibration_verification(
            participant_id=payload.participant_id,
            calibration_profile_id=system_profile.id,
            operator_id=identity.user_id if identity else None,
            passed=not failed,
            checks_json=json.dumps(automatic_checks, sort_keys=True),
        )
        repository.add_audit_event(
            "session.automatic_readiness", str(verification.id),
            request.client.host if request.client else None,
            success=not failed, details=f"participant={payload.participant_id}",
        )
        if failed:
            first = failed[0]
            detail = str(first.get("detail") or "Not ready")
            raise HTTPException(
                status_code=409,
                detail=f"{first['label']} needs attention: {detail}. Adjust the camera or participant, then select Start session again.",
            )
    try:
        identity = token_identity(request.cookies.get(COOKIE_NAME))
        session_notes = payload.notes
        item = session_manager.start(payload.participant_id, session_notes,
                                     identity.user_id if identity else None)
    except SessionConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    result = session_payload(item)
    repository.add_audit_event("session.start", str(item.id), request.client.host if request.client else None)
    result["session_time"] = session_manager.elapsed()
    return result


@router.post("/sessions/{session_id}/stop")
def stop_session(session_id: int, request: Request, payload: SessionStop | None = None) -> dict[str, object]:
    _require_session_access(request, session_id)
    attention_status = attention_task_service.status()
    if attention_status.get("session_id") == session_id and attention_status.get("run_id") is not None:
        attention_task_service.abort()
    research_status = research_task_service.status()
    if research_status.get("session_id") == session_id and research_status.get("active"):
        research_task_service.abort()
    try:
        item = session_manager.stop(session_id, payload.notes if payload else None)
    except SessionConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    repository.add_audit_event("session.stop", str(session_id), request.client.host if request.client else None)
    return {"session_id": item.session_id, "duration_seconds": item.duration_seconds,
            "total_blinks": item.total_blinks, "average_blink_rate": item.average_blink_rate,
            "head_movements": item.head_movements, "body_movement_events": item.body_movement_events,
            "posture_changes": item.posture_changes, "mock_data": item.mock_data,
            "created_at": item.created_at.isoformat()}


@router.get("/sessions/{session_id}")
def get_session(session_id: int, request: Request) -> dict[str, object]:
    _require_session_access(request, session_id)
    item = repository.get_session(session_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Session not found")
    result = session_payload(item)
    result["session_time"] = session_manager.elapsed() if session_manager.active_session_id == session_id else None
    return result


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: int, request: Request, confirm: bool = Query(False)) -> Response:
    if not confirm:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required")
    _require_session_access(request, session_id)
    try:
        repository.delete_session(session_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RecordDeleteConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    repository.add_audit_event("session.delete", str(session_id),
                               request.client.host if request.client else None)
    return Response(status_code=204)


@router.get("/sessions/{session_id}/summary")
def get_session_summary(session_id: int, request: Request) -> dict[str, object]:
    _require_session_access(request, session_id)
    item = repository.get_summary(session_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Session summary not found")
    return {"session_id": item.session_id, "duration_seconds": item.duration_seconds,
            "total_blinks": item.total_blinks, "average_blink_rate": item.average_blink_rate,
            "head_movements": item.head_movements, "body_movement_events": item.body_movement_events,
            "posture_changes": item.posture_changes, "mock_data": item.mock_data,
            "details": json.loads(item.summary_json), "created_at": item.created_at.isoformat()}


@router.post("/attention/start")
def start_attention_task(payload: AttentionTaskStart, request: Request) -> dict[str, object]:
    _require_active_task_access(request)
    if shape_matching.active_run(session_manager.active_session_id):
        raise HTTPException(status_code=409, detail="Finish the Shape Matching run before launching balloons")
    try:
        return attention_task_service.start(
            task_key=payload.task_key, age_profile=payload.age_profile,
            difficulty=payload.difficulty, required_pops=payload.required_pops,
            game_mode=payload.game_mode, target_color=payload.target_color,
            sound_enabled=payload.sound_enabled,
            maximum_duration_seconds=payload.maximum_duration_seconds)
    except AttentionTaskConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))


class ShapeStart(BaseModel):
    count: int = Field(default=10, ge=5, le=50)


class ShapeRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trial: int = Field(ge=1, le=50, strict=True)
    shape: str = Field(pattern=r"^(circle|square|triangle|star)$")
    outcome: str = Field(pattern=r"^(matched|timeout|assistance_limit|stopped)$")
    active_ms: int = Field(ge=0, le=31000, strict=True)
    wrong_drops: int = Field(ge=0, le=3, strict=True)
    first_attempt_correct: bool = Field(strict=True)


@router.post("/shape-matching/stop-active")
def stop_active_shape(request: Request):
    _require_active_task_access(request)
    if not session_manager.active_session_id:
        raise HTTPException(status_code=409, detail="No active monitoring session")
    result = shape_matching.stop_active(session_manager.active_session_id)
    if result["stopped_runs"]: session_manager.set_phase("post_task")
    return result


@router.post("/shape-matching/runs", status_code=201)
def create_shape_run(payload: ShapeStart, request: Request):
    _require_active_task_access(request)
    session_id = session_manager.active_session_id
    if not session_id:
        raise HTTPException(status_code=409, detail="Start a participant session first")
    if attention_task_service.public_status()["phase"] in {"recording", "paused", "practice"}:
        raise HTTPException(status_code=409, detail="End the balloon activity before launching Shape Matching")
    try:
        result = shape_matching.create_run(session_id, payload.count)
        result["url"] = f"/shape-matching?token={result.pop('token')}"
        return result
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


def shape_action(token, action="status", row=None):
    try:
        result = shape_matching.operate(token, action, row)
        changed = result.pop("_status_changed", False)
        if changed and action == "start" and result["status"] == "recording":
            session_manager.set_phase("task")
        elif changed and action in {"trial", "stop"} and result["status"] in {"complete", "stopped"}:
            session_manager.set_phase("post_task")
        return result
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/participant-task/shape/status")
def shape_status(token: str = Query(min_length=30, max_length=100)):
    return shape_action(token)


@router.post("/participant-task/shape/action/{action}")
def shape_control(action: str, token: str = Query(min_length=30, max_length=100)):
    if action not in {"start", "pause", "resume", "stop"}:
        raise HTTPException(status_code=404, detail="Unknown action")
    return shape_action(token, action)


@router.post("/participant-task/shape/trial")
def shape_trial(payload: ShapeRow, token: str = Query(min_length=30, max_length=100)):
    return shape_action(token, "trial", payload.model_dump())


@router.get("/attention/status")
def attention_status(request: Request) -> dict[str, object]:
    _require_active_task_access(request)
    return {**attention_task_service.status(), **attention_task_service.public_status()}


@router.get("/attention/catalog")
def attention_catalog() -> dict[str, object]:
    return task_catalog()


@router.post("/attention/practice")
def prepare_attention_practice(payload: AttentionPracticeStart, request: Request) -> dict[str, object]:
    _require_active_task_access(request)
    if shape_matching.active_run(session_manager.active_session_id):
        raise HTTPException(status_code=409, detail="Finish the Shape Matching run before balloon practice")
    try:
        return attention_task_service.prepare_practice(**payload.model_dump())
    except AttentionTaskConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/attention/practice/cancel")
def cancel_attention_practice(request: Request) -> dict[str, object]:
    _require_active_task_access(request)
    try:
        return attention_task_service.cancel_practice()
    except AttentionTaskConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))


def _participant_display_url(request: Request, token: str) -> str:
    """Return a tablet-reachable LAN URL instead of loopback when possible."""
    host = request.url.hostname or "127.0.0.1"
    if host in {"127.0.0.1", "localhost", "::1"}:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("8.8.8.8", 80))
            host = probe.getsockname()[0]
        except OSError:
            host = "127.0.0.1"
        finally:
            probe.close()
    port = request.url.port
    authority = f"{host}:{port}" if port else host
    return f"{request.url.scheme}://{authority}/attention-task?token={token}"


@router.get("/participant-display/info")
def participant_display_info(request: Request) -> dict[str, str]:
    _require_active_task_access(request)
    identity = _request_identity(request)
    if identity and identity.role == "reviewer":
        raise HTTPException(status_code=403, detail="Reviewer access is read-only")
    pairing = attention_task_service.pair_display()
    token = str(pairing["token"])
    return {"url": _participant_display_url(request, token),
            "qr_url": f"/api/participant-display/qr.svg?token={token}",
            "expires_in_seconds": str(pairing["expires_in_seconds"])}


@router.get("/participant-display/connection")
def participant_display_connection(request: Request) -> dict[str, object]:
    _require_setup_admin(request)
    status = attention_task_service.public_status()
    return {"connected": bool(status.get("display_connected")),
            "phase": status.get("phase"), "detail": ("Participant screen heartbeat received"
            if status.get("display_connected") else "Open the QR/link on the participant device")}


@router.get("/participant-display/qr.svg")
def participant_display_qr(request: Request, token: str = Query(min_length=20, max_length=100)) -> Response:
    if not attention_task_service.validate_display_token(token, mark_seen=False):
        raise HTTPException(status_code=401, detail="Participant display pairing expired")
    image = qrcode.make(_participant_display_url(request, token), image_factory=qrcode.image.svg.SvgPathImage,
                        box_size=8, border=2)
    output = image.to_string(encoding="unicode")
    return Response(content=output, media_type="image/svg+xml",
                    headers={"Cache-Control": "no-store"})


def _require_display_token(token: str) -> None:
    if not attention_task_service.validate_display_token(token):
        raise HTTPException(status_code=401, detail="Participant display pairing expired")


@router.get("/participant-task/status")
def participant_task_status(token: str = Query(min_length=20, max_length=100)) -> dict[str, object]:
    _require_display_token(token)
    return attention_task_service.public_status()


@router.post("/participant-task/practice-complete")
def participant_practice_complete(token: str = Query(min_length=20, max_length=100),
                                  generation: int | None = Query(default=None, ge=1)) -> dict[str, object]:
    _require_display_token(token)
    try:
        return attention_task_service.complete_practice(generation)
    except AttentionTaskConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/participant-task/practice-cancel")
def participant_practice_cancel(token: str = Query(min_length=20, max_length=100),
                                generation: int | None = Query(default=None, ge=1)) -> dict[str, object]:
    _require_display_token(token)
    try:
        return attention_task_service.cancel_practice(generation)
    except AttentionTaskConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/participant-task/practice-help")
def participant_practice_help(token: str = Query(min_length=20, max_length=100),
                              generation: int | None = Query(default=None, ge=1)) -> dict[str, object]:
    _require_display_token(token)
    try:
        return attention_task_service.practice_needs_help(generation)
    except AttentionTaskConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/participant-task/abort")
def participant_task_abort(token: str = Query(min_length=20, max_length=100)) -> dict[str, object]:
    _require_display_token(token)
    return attention_task_service.abort()


@router.post("/participant-task/recover")
def participant_task_recover(token: str = Query(min_length=20, max_length=100)) -> dict[str, object]:
    _require_display_token(token)
    return attention_task_service.recover_display()


@router.post("/participant-task/pause")
def participant_task_pause(token: str = Query(min_length=20, max_length=100)) -> dict[str, object]:
    _require_display_token(token)
    try:
        return attention_task_service.pause()
    except AttentionTaskConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/participant-task/trials/next")
def participant_next_trial(token: str = Query(min_length=20, max_length=100)) -> dict[str, object]:
    _require_display_token(token)
    try:
        return attention_task_service.next_trial()
    except AttentionTaskConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/participant-task/trials/{trial_id}/complete")
def participant_complete_trial(trial_id: int, payload: TrialComplete,
                               token: str = Query(min_length=20, max_length=100)) -> dict[str, object]:
    _require_display_token(token)
    if payload.responded and payload.reaction_time_ms is None:
        raise HTTPException(status_code=422, detail="reaction_time_ms is required for a response")
    try:
        return attention_task_service.complete_trial(
            trial_id, payload.responded, payload.reaction_time_ms, payload.premature_taps)
    except AttentionTaskConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/participant-task/trials/{trial_id}/status")
def participant_trial_status(trial_id: int,
                             token: str = Query(min_length=20, max_length=100)) -> dict[str, object]:
    _require_display_token(token)
    try:
        return attention_task_service.completed_trial_status(trial_id)
    except AttentionTaskConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/attention/abort")
def abort_attention_task(request: Request, payload: AttentionAbort | None = None) -> dict[str, object]:
    _require_active_task_access(request)
    result = attention_task_service.abort(payload.reason if payload else "operator_ended")
    repository.add_audit_event("attention.abort", str(result["session_id"]) if result["session_id"] else None,
                               request.client.host if request.client else None)
    return result


@router.post("/attention/trials/next")
def next_attention_trial(request: Request) -> dict[str, object]:
    _require_active_task_access(request)
    try:
        return attention_task_service.next_trial()
    except AttentionTaskConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/attention/pause")
def pause_attention_task(request: Request) -> dict[str, object]:
    _require_active_task_access(request)
    try:
        return attention_task_service.pause()
    except AttentionTaskConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/attention/resume")
def resume_attention_task(request: Request) -> dict[str, object]:
    _require_active_task_access(request)
    try:
        return attention_task_service.resume()
    except AttentionTaskConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/attention/trials/{trial_id}/complete")
def complete_attention_trial(trial_id: int, payload: TrialComplete, request: Request) -> dict[str, object]:
    _require_active_task_access(request)
    if payload.responded and payload.reaction_time_ms is None:
        raise HTTPException(status_code=422, detail="reaction_time_ms is required for a response")
    try:
        return attention_task_service.complete_trial(
            trial_id, payload.responded, payload.reaction_time_ms, payload.premature_taps)
    except AttentionTaskConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/attention/sessions/{session_id}/summary")
def attention_summary(session_id: int, request: Request) -> dict[str, object]:
    _require_session_access(request, session_id)
    return attention_task_service.summary(session_id)


@router.get("/research-tasks/protocols")
def research_protocols() -> list[dict[str, object]]:
    return protocol_catalog()


@router.get("/research-tasks/status")
def research_task_status(request: Request) -> dict[str, object]:
    _require_active_task_access(request)
    return research_task_service.status()


@router.post("/research-tasks/start", status_code=201)
def start_research_task(payload: ResearchTaskStart, request: Request) -> dict[str, object]:
    _require_active_task_access(request)
    try:
        result = research_task_service.start(
            payload.protocol_key, seed=payload.random_seed,
            gaze_provider=payload.gaze_provider, gaze_validated=payload.gaze_validated,
        )
    except ResearchTaskConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    repository.add_audit_event("research_task.start", str(result.get("run_id")),
                               request.client.host if request.client else None,
                               details=f"{payload.protocol_key}")
    return result


@router.post("/research-tasks/trials/next")
def next_research_trial(request: Request) -> dict[str, object]:
    _require_active_task_access(request)
    try:
        return research_task_service.next_trial()
    except ResearchTaskConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/research-tasks/trials/{trial_id}/complete")
def complete_research_trial(trial_id: int, payload: ResearchTrialComplete, request: Request) -> dict[str, object]:
    _require_active_task_access(request)
    try:
        return research_task_service.complete_trial(
            trial_id, observed_direction=payload.observed_direction,
            response_latency_ms=payload.response_latency_ms,
            client_started_ms=payload.client_started_ms,
            client_completed_ms=payload.client_completed_ms,
            tracking_valid=payload.tracking_valid,
            invalid_reason=payload.invalid_reason, metrics=payload.metrics,
        )
    except ResearchTaskConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/research-tasks/abort")
def abort_research_task(request: Request) -> dict[str, object]:
    _require_active_task_access(request)
    result = research_task_service.abort()
    repository.add_audit_event("research_task.abort", str(result.get("run_id")),
                               request.client.host if request.client else None)
    return result


@router.get("/reports/{session_id}")
def session_report(session_id: int, request: Request) -> dict[str, object]:
    _require_session_access(request, session_id)
    report = repository.build_report(session_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return report


@router.get("/exports/sessions/{session_id}.json")
def export_session_json(session_id: int, request: Request) -> Response:
    _require_session_access(request, session_id)
    content = session_json(session_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Session not found")
    repository.add_audit_event("export.session_json", str(session_id), request.client.host if request.client else None)
    return Response(content=content, media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="session-{session_id}.json"'})


@router.get("/exports/sessions/{session_id}.zip")
def export_session_zip(session_id: int, request: Request) -> Response:
    _require_session_access(request, session_id)
    content = session_archive(session_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Session not found")
    repository.add_audit_event("export.session_zip", str(session_id), request.client.host if request.client else None)
    return Response(content=content, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="session-{session_id}-research-data.zip"'})


@router.get("/exports/database-backup.zip")
def export_database_backup(request: Request) -> Response:
    try:
        content = database_backup_archive()
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    repository.add_audit_event("export.database_backup", None, request.client.host if request.client else None)
    return Response(content=content, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="database-backup-{stamp}.zip"'})


@router.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "application": settings.app_name,
        "mode": settings.app_mode,
        "raw_video_recording": settings.save_raw_video,
    }


@router.get("/system/status")
def system_status() -> dict[str, object]:
    process = psutil.Process(os.getpid())
    return {
        "uptime_seconds": round(time.monotonic() - SERVER_STARTED, 1),
        "process_memory_mb": round(process.memory_info().rss / 1024 / 1024, 1),
        "cpu_percent": process.cpu_percent(interval=None),
        "ai_device": "CUDA" if torch.cuda.is_available() else "CPU",
        "cuda_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "versions": {name: importlib.metadata.version(name) for name in
                     ("fastapi", "uvicorn", "sqlalchemy", "opencv-contrib-python", "mediapipe", "ultralytics", "torch")},
        "camera": camera_system.status(),
        "face_worker": face_analysis_service.snapshot(),
        "body_worker": body_analysis_service.snapshot(),
        "active_session_id": session_manager.active_session_id,
        "session_time": session_manager.elapsed(),
        "raw_video_recording": settings.save_raw_video,
    }


@router.get("/settings")
def get_settings() -> dict[str, object]:
    return {"settings": current_settings(), "restart_required": False, "env_file": ".env"}


@router.put("/settings")
def update_settings(payload: SettingsUpdate, request: Request) -> dict[str, object]:
    if session_manager.active_session_id is not None:
        raise HTTPException(status_code=409, detail="Stop the active session before changing system settings")
    if payload.save_raw_video:
        raise HTTPException(status_code=422, detail="Raw-video recording cannot be enabled from the prototype UI")
    if (not settings.mock_mode and
            str(payload.face_camera_source).strip() == str(payload.body_camera_source).strip()):
        raise HTTPException(
            status_code=422,
            detail=("Face and body camera sources must be different. One USB webcam can be "
                    "previewed for setup, but two-camera monitoring requires a second webcam."),
        )
    try:
        validate_selection(payload.face_display_groups, payload.face_measure_groups,
                           payload.body_display_groups, payload.body_measure_groups, payload.feature_types)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    save_settings(payload.model_dump())
    repository.add_audit_event("settings.update", None, request.client.host if request.client else None)
    return {"status": "saved", "restart_required": True,
            "message": "Settings saved. Restart the server to apply them."}


@router.get("/audit")
def audit_events(limit: int = Query(default=100, ge=1, le=500)) -> list[dict[str, object]]:
    return [{"id": item.id, "occurred_at": item.occurred_at.isoformat(), "action": item.action,
             "subject": item.subject, "client_ip": item.client_ip, "success": item.success,
             "details": item.details} for item in repository.list_audit_events(limit)]


@router.get("/calibration/readiness")
def get_calibration_readiness() -> dict[str, object]:
    return calibration_readiness()


@router.get("/calibration/status")
def get_calibration_status(request: Request,
                           participant_id: int | None = Query(default=None, gt=0)) -> dict[str, object]:
    identity = _request_identity(request)
    system_profile = repository.latest_accepted_calibration_type("system")
    verification = None
    verification_fresh = False
    if participant_id is not None:
        _require_participant_access(request, participant_id)
        verification = repository.latest_passing_verification(
            participant_id, identity.user_id if identity and identity.role == "operator" else None)
        if verification is not None:
            verified_at = verification.created_at
            if verified_at.tzinfo is None:
                verified_at = verified_at.replace(tzinfo=timezone.utc)
            verification_fresh = (datetime.now(timezone.utc) - verified_at <= timedelta(minutes=15)
                                  and system_profile is not None
                                  and verification.calibration_profile_id == system_profile.id)
    setup_changed = bool(system_profile and system_profile.configuration_hash != configuration_hash())
    system_ready = system_profile is not None and not setup_changed
    # The accepted one-time setup is the calibration gate. Participant checks are
    # now automatic and are recorded when Start session is selected.
    ready = system_ready
    if setup_changed:
        message = "Camera or analysis settings changed — repeat System / Room Calibration."
        next_step = "system"
    elif not system_ready:
        message = "System / Room Calibration is required before the first session."
        next_step = "system"
    else:
        message = "System calibration is saved. Live cameras and framing will be checked automatically when the session starts."
        next_step = "ready"
    return {"ready": ready, "system_ready": system_ready,
            "participant_baseline_ready": True,
            "session_verification_ready": verification_fresh,
            "participant_id": participant_id, "next_step": next_step, "message": message,
            "system_profile_id": system_profile.id if system_profile else None,
            "system_calibrated_at": (system_profile.accepted_at or system_profile.created_at).isoformat() if system_profile else None,
            "setup_changed": setup_changed,
            "participant_profile_id": None,
            "verification_valid_minutes": 15}


@router.get("/performance/health")
def performance_health() -> dict[str, object]:
    cameras = camera_system.status(); face = face_analysis_service.snapshot(); body = body_analysis_service.snapshot()
    face_health = evaluate_pipeline("face", cameras["face"], face, mock=settings.mock_mode)
    body_health = evaluate_pipeline("body", cameras["body"], body, mock=settings.mock_mode)
    order = {"green": 0, "yellow": 1, "red": 2}
    overall = max((face_health["level"], body_health["level"]), key=order.get)
    return {"overall": overall, "face": face_health, "body": body_health,
            "legend": {"green": "Ready", "yellow": "Review before recording", "red": "Do not record"}}


@router.get("/calibration/profiles")
def list_calibration_profiles(request: Request, participant_id: int | None = Query(default=None, gt=0)) -> list[dict[str, object]]:
    identity = _request_identity(request)
    items = repository.list_calibration_profiles(participant_id)
    if identity and identity.role in {"operator", "reviewer"}:
        allowed = {p.id for p in repository.list_participants(identity.user_id)}
        items = [item for item in items if item.profile_type == "system" or item.participant_id in allowed]
    return [calibration_payload(item, include_details=False) for item in items]


@router.get("/calibration/profiles/{profile_id}")
def get_calibration_profile(profile_id: int, request: Request) -> dict[str, object]:
    item = repository.get_calibration_profile(profile_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Calibration profile not found")
    _require_calibration_access(request, item)
    return calibration_payload(item)


@router.post("/calibration/profiles", status_code=201)
def save_calibration_profile(data: CalibrationCreate, request: Request) -> dict[str, object]:
    if session_manager.active_session_id is not None:
        raise HTTPException(status_code=409, detail="Stop the active session before saving calibration")
    identity = _request_identity(request)
    if identity and identity.role not in {"owner", "admin", "operator"}:
        raise HTTPException(status_code=403, detail="Only Owner or device operator can save system calibration")
    if data.participant_id is not None:
        raise HTTPException(status_code=422, detail="System calibration cannot be linked to a participant")
    # Drafts may be incomplete; acceptance validates the complete setup.
    item = create_profile(data.name, data.participant_id, data.manual_checks, data.notes,
                          data.profile_type, identity.user_id if identity else None)
    repository.add_audit_event("calibration.create", str(item.id), request.client.host if request.client else None)
    return calibration_payload(item)


@router.post("/calibration/profiles/{profile_id}/accept")
def accept_calibration_profile(profile_id: int, request: Request) -> dict[str, object]:
    existing = repository.get_calibration_profile(profile_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Calibration profile not found")
    identity = _request_identity(request)
    if existing.profile_type == "system" and identity and identity.role not in {"owner", "admin", "operator"}:
        raise HTTPException(status_code=403, detail="Only Owner or device operator can accept system calibration")
    if existing.participant_id is not None:
        _require_participant_access(request, existing.participant_id)
    if not settings.mock_mode:
        if existing.configuration_hash != configuration_hash():
            raise HTTPException(status_code=409, detail="Setup changed after this draft was saved. Save a replacement profile before acceptance.")
        manual = json.loads(existing.manual_checks_json)
        required = {"camera_roles", "lighting", "face_framing", "body_framing",
                    "participant_position", "body_controlled_test", "attention_practice",
                    "chair_adjusted", "distractions_removed", "reflection_checked", "instructions_understood"}
        if not calibration_readiness()["ready"] or not all(manual.get(key) for key in required):
            raise HTTPException(status_code=409, detail="Complete camera, placement, face, body and activity checks before accepting this draft.")
    try:
        item = repository.accept_calibration_profile(profile_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    repository.add_audit_event("calibration.accept", str(profile_id), request.client.host if request.client else None)
    return calibration_payload(item)


@router.post("/calibration/verify", status_code=201)
def verify_calibration(data: CalibrationVerificationCreate, request: Request) -> dict[str, object]:
    _require_participant_access(request, data.participant_id)
    system_profile = repository.latest_accepted_calibration_type("system")
    if system_profile is None:
        raise HTTPException(status_code=409, detail="Owner or device operator must complete System / Room Calibration first")
    if not settings.mock_mode:
        if system_profile.configuration_hash != configuration_hash():
            raise HTTPException(status_code=409, detail="Room configuration changed. Accept a replacement setup first")
        if not all(check_allowed(item) for item in calibration_readiness()["checks"] if item["id"] not in {"face_calibration", "head_calibration"}):
            raise HTTPException(status_code=409, detail="Check both camera connections and participant framing before confirming readiness")
    checks = data.model_dump(exclude={"participant_id"})
    passed = all(checks.values())
    identity = _request_identity(request)
    item = repository.create_calibration_verification(
        participant_id=data.participant_id, calibration_profile_id=system_profile.id,
        operator_id=identity.user_id if identity else None, passed=passed,
        checks_json=json.dumps(checks, sort_keys=True))
    repository.add_audit_event("calibration.verify", str(item.id),
                               request.client.host if request.client else None,
                               success=passed, details=f"participant={data.participant_id}")
    return {"id": item.id, "participant_id": item.participant_id, "passed": item.passed,
            "valid_for_minutes": 15, "created_at": item.created_at.isoformat(), "checks": checks}


@router.delete("/calibration/profiles/{profile_id}", status_code=204)
def delete_calibration_profile(profile_id: int, request: Request, confirm: bool = Query(False)) -> Response:
    if not confirm:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required")
    existing = repository.get_calibration_profile(profile_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Calibration profile not found")
    _require_calibration_access(request, existing)
    identity = _request_identity(request)
    if existing.profile_type == "system" and identity and identity.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Only Owner/Admin can delete system calibration")
    try:
        repository.delete_calibration_profile(profile_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RecordDeleteConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    repository.add_audit_event("calibration.delete", str(profile_id), request.client.host if request.client else None)
    return Response(status_code=204)


@router.get("/hardware/validation")
def hardware_validation() -> dict[str, object]:
    return validation_report()


@router.get("/hardware/rpi-health")
def raspberry_pi_health() -> dict[str, object]:
    url = node_health_url()
    if url is None:
        return {"configured": False, "reachable": False, "detail": "Camera sources are not Raspberry Pi network URLs"}
    try:
        response = httpx.get(url, timeout=2.0)
        return {"configured": True, "reachable": response.is_success, "url": url,
                "status_code": response.status_code, "node": response.json() if response.is_success else None}
    except (httpx.HTTPError, ValueError) as exc:
        return {"configured": True, "reachable": False, "url": url, "detail": str(exc)}


@router.get("/cameras/status")
def camera_status() -> dict[str, object]:
    return camera_system.status()


@router.get("/cameras/discover")
def camera_discovery(max_index: int = Query(default=5, ge=1, le=10)) -> dict[str, object]:
    # Never reopen an index already owned by a capture thread. Some Windows
    # camera drivers fail inside native code when the same device is probed.
    active_indexes = {
        source for source in (camera_system.face.source, camera_system.body.source)
        if isinstance(source, int)
    }
    status = camera_system.status()
    cameras = []
    for index in sorted(active_indexes):
        owner = "face" if camera_system.face.source == index else "body"
        details = status[owner]
        cameras.append({"index": index, "available": details["status"] == "CONNECTED",
                        "width": details.get("width", 0), "height": details.get("height", 0),
                        "fps": details.get("capture_fps", 0), "in_use": True,
                        "assigned_to": owner})
    cameras.extend(discover_usb_cameras(max_index, active_indexes))
    cameras.sort(key=lambda item: int(item["index"]))
    return {"cameras": cameras}


@router.get("/monitor/snapshot")
def monitor_snapshot() -> dict[str, object]:
    if settings.mock_mode:
        return mock_monitor.snapshot()
    return {"data_mode": "REAL CAMERA DATA", "face": face_analysis_service.snapshot()}


@router.get("/face/status")
def face_status() -> dict[str, object]:
    if settings.mock_mode:
        return {
            "tracking": True, "status": "MOCK", "left_ear": 0.29, "right_ear": 0.29,
            "average_ear": 0.29, "eye_closed": False, "total_blinks": 0,
            "blink_rate": 16.0, "processing_fps": settings.face_process_fps,
            "threshold": settings.ear_threshold, "calibrated": False,
            "calibration_status": "MOCK — calibration not required",
        }
    return face_analysis_service.snapshot()


@router.post("/face/calibration/start")
def start_face_calibration(duration_seconds: float = Query(default=10.0, ge=5.0, le=30.0)) -> dict[str, object]:
    if settings.mock_mode:
        invalidate_direction_progress()
        return {"status": "started", "duration_seconds": duration_seconds, "simulation": True}
    invalidate_direction_progress()
    face_analysis_service.start_calibration(duration_seconds)
    return {"status": "started", "duration_seconds": duration_seconds}


@router.get("/head/status")
def head_status() -> dict[str, object]:
    if settings.mock_mode:
        return {
            "yaw": -4.2, "pitch": 2.1, "roll": 0.8, "direction": "CENTER",
            "horizontal": "CENTER", "vertical": "CENTER", "tilt": "LEVEL",
            "magnitude": 4.8, "movement_event": False, "total_movements": 0,
            "movements_per_minute": 0.0, "calibrated": False,
            "calibration_status": "MOCK — calibration not required",
        }
    face = face_analysis_service.snapshot()
    return {
        "yaw": face["yaw"], "pitch": face["pitch"], "roll": face["roll"],
        "direction": face["head_direction"], "magnitude": face["head_movement_magnitude"],
        "horizontal": face["horizontal_direction"], "vertical": face["vertical_direction"],
        "tilt": face["head_tilt"],
        "movement_event": face["head_movement_event"], "total_movements": face["head_movements"],
        "movements_per_minute": face["head_movements_per_minute"],
        "calibrated": face["head_calibrated"], "calibration_status": face["head_calibration_status"],
    }


@router.post("/head/calibration/start")
def start_head_calibration(duration_seconds: float = Query(default=10.0, ge=5.0, le=30.0)) -> dict[str, object]:
    if settings.mock_mode:
        invalidate_direction_progress()
        return {"status": "started", "duration_seconds": duration_seconds, "simulation": True}
    invalidate_direction_progress()
    face_analysis_service.start_head_calibration(duration_seconds)
    return {"status": "started", "duration_seconds": duration_seconds}


@router.get("/body/status")
def body_status() -> dict[str, object]:
    if settings.mock_mode:
        return {
            "tracking": True, "status": "MOCK", "device": "CPU", "processing_fps": settings.body_process_fps,
            "person_count": 1, "primary_subject_index": 0, "movement_magnitude": 0.31,
            "regional_movement": {"head_shoulders": 0.08, "left_arm": 0.12, "right_arm": 0.1,
                                  "torso": 0.04, "left_leg": 0.09, "right_leg": 0.11},
            "movement_event": False, "movement_events": 0, "movements_per_minute": 0.0,
            "posture_change": False, "posture_changes": 0, "posture_angle": 0.0,
            "body_scale": 300.0, "model_status": "MOCK",
        }
    return body_analysis_service.snapshot()
