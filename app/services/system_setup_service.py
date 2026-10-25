"""Durable first-run setup state and focused repair routing."""

from __future__ import annotations

import json
import importlib.util
import importlib.metadata
import os
import shutil
import tempfile
from datetime import datetime, timezone
from typing import Any

from app.config import ROOT_DIR, settings
from app.database.repository import repository
from app.database.database import SessionLocal
from sqlalchemy import text
from app.services.calibration_service import SCHEMA_VERSION, configuration_hash, create_profile, readiness

STEP_COUNT = 6
STEP_NAMES = (
    "System check", "Camera connection", "Camera assignment",
    "Room placement", "System calibration", "Connectivity and review",
)
DIRECTION_SEQUENCE = ("UP", "DOWN", "LEFT", "RIGHT", "CENTER")
# Persistent setup health. Face/body tracking are intentionally excluded: they
# describe the participant currently standing in front of the cameras, not the
# saved room/camera configuration. Participant presence is checked in Step 5
# and again by the automatic readiness sample when a session starts.
CRITICAL_READINESS = {
    "face_camera": 2, "body_camera": 2,
    "face_fps": 3, "body_fps": 3,
    "face_calibration": 5, "head_calibration": 5,
    "privacy": 1,
}


def _progress(item) -> dict[str, Any]:
    try:
        value = json.loads(item.progress_json) if item else {}
        return value if isinstance(value, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def _system_checks() -> list[dict[str, Any]]:
    data_dir = ROOT_DIR / "data"
    model = ROOT_DIR / settings.pose_model
    dependencies = ("fastapi", "cv2", "mediapipe", "ultralytics", "sqlalchemy")
    missing = [name for name in dependencies if importlib.util.find_spec(name) is None]
    database_ok, database_detail = False, "Unavailable"
    try:
        with SessionLocal() as db:
            database_ok = db.execute(text("SELECT 1")).scalar_one() == 1
            database_detail = "Read/write engine connected" if database_ok else "Unexpected database response"
    except Exception as exc:
        database_detail = f"Database check failed: {type(exc).__name__}"
    storage_ok, storage_detail = False, str(data_dir)
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=data_dir, prefix="setup-check-", delete=True) as handle:
            handle.write(b"ok"); handle.flush()
        free_gb = shutil.disk_usage(data_dir).free / (1024 ** 3)
        storage_ok = free_gb >= 1.0
        storage_detail = f"Writable · {free_gb:.1f} GB free"
    except OSError as exc:
        storage_detail = f"Storage check failed: {type(exc).__name__}"
    versions = []
    for name in dependencies:
        try:
            package = "opencv-contrib-python" if name == "cv2" else name
            versions.append(f"{name} {importlib.metadata.version(package)}")
        except importlib.metadata.PackageNotFoundError:
            pass
    checks = [
        {"id": "server", "label": "Application server", "passed": True, "detail": "Running"},
        {"id": "database", "label": "Local database", "passed": database_ok, "detail": database_detail},
        {"id": "storage", "label": "Data storage", "passed": storage_ok, "detail": storage_detail},
        {"id": "dependencies", "label": "Required software", "passed": not missing,
         "detail": ", ".join(versions) if not missing else f"Missing: {', '.join(missing)}"},
        {"id": "pose_model", "label": "Body tracking model", "passed": settings.mock_mode or (model.is_file() and os.access(model, os.R_OK) and model.stat().st_size > 0),
         "detail": "Simulation mode" if settings.mock_mode else (f"Readable · {model.stat().st_size / 1024 / 1024:.1f} MB" if model.is_file() else "File missing")},
        {"id": "privacy", "label": "Raw video recording", "passed": not settings.save_raw_video,
         "detail": "Disabled" if not settings.save_raw_video else "Must be disabled"},
    ]
    return checks


def status_payload() -> dict[str, Any]:
    item = repository.get_system_setup_state()
    progress = _progress(item)
    current_hash = configuration_hash()
    setup_status = item.status if item else "setup_required"
    repair_step = None
    message = "Complete the one-time setup before starting daily operation."
    critical: list[dict[str, Any]] = []
    hash_valid = bool(item and item.completed_at and item.configuration_hash == current_hash)
    if item and item.completed_at:
        if item.configuration_hash != current_hash:
            setup_status = "setup_required"; repair_step = 2
            message = "Camera or measurement settings changed. Review the camera setup."
        else:
            live = readiness()
            critical = [c for c in live["checks"] if c["id"] in CRITICAL_READINESS and not c["passed"]]
            if critical:
                repair_step = min(CRITICAL_READINESS.get(str(c["id"]), 5) for c in critical)
                setup_status = "needs_attention"
                message = f"{critical[0]['label']} needs attention. Open the focused repair step."
            else:
                setup_status = "ready"
                message = "System setup is complete. Daily operation is ready."
    step = repair_step or (item.current_step if item else 1)
    return {
        "status": setup_status, "completed": bool(item and item.completed_at),
        "can_operate": hash_valid, "can_start": hash_valid and not critical,
        "critical_issues": [check["label"] for check in critical],
        "current_step": max(1, min(STEP_COUNT, int(step or 1))), "total_steps": STEP_COUNT,
        "step_names": STEP_NAMES, "repair_step": repair_step, "message": message,
        "progress": progress, "configuration_changed": bool(item and item.completed_at and item.configuration_hash != current_hash),
        "configuration_hash": current_hash,
        "completed_at": item.completed_at.isoformat() if item and item.completed_at else None,
        "completed_by": item.completed_by_name if item else None,
        "calibration_version": item.calibration_version if item else None,
        "system_checks": _system_checks(),
        "step_completion": _step_completion(progress),
        "direction_sequence": list(DIRECTION_SEQUENCE),
    }


def _step_completion(progress: dict[str, Any]) -> dict[str, bool]:
    step_1 = progress.get("step_1", {})
    step_2 = progress.get("step_2", {})
    step_3 = progress.get("step_3", {})
    step_4 = progress.get("step_4", {})
    step_5 = progress.get("step_5", {})
    directions = tuple(step_5.get("directions_passed") or ())
    step_6 = progress.get("step_6", {})
    connection_mode = step_2.get("connection_mode")
    connectivity_ready = bool(step_6.get("participant_connected"))
    if connection_mode == "rpi":
        connectivity_ready = connectivity_ready and bool(step_6.get("rpi_reachable"))
    return {
        "1": bool(step_1.get("passed")),
        "2": bool(step_2.get("connection_mode")),
        "3": bool(step_3.get("face_source") and step_3.get("body_source") and not step_3.get("restart_required")),
        "4": all(step_4.get(key) is True for key in ("lighting", "face_framing", "body_framing", "distance")),
        "5": bool(step_5.get("ready") and directions == DIRECTION_SEQUENCE),
        "6": connectivity_ready and bool(step_6.get("connectivity_reviewed")),
    }


def save_progress(step: int, values: dict[str, Any]) -> dict[str, Any]:
    if not 1 <= step <= STEP_COUNT:
        raise ValueError("Setup step must be between 1 and 6")
    item = repository.get_system_setup_state()
    progress = _progress(item)
    if step == 5:
        live = readiness()
        if not live["ready"]:
            failed = ", ".join(check["label"] for check in live["checks"] if not check["passed"])
            raise ValueError(f"Complete system calibration before continuing: {failed}")
        # Direction progress is produced by record_direction_observation(), not
        # trusted from the browser payload. Add a durable server-side snapshot
        # proving that all live checks passed at this point in the workflow.
        saved = dict(progress.get("step_5", {}))
        directions = list(saved.get("directions_passed") or ())
        if tuple(directions) != DIRECTION_SEQUENCE:
            raise ValueError("Complete UP, DOWN, LEFT, RIGHT, and CENTER before continuing")
        values = {
            **saved,
            **values,
            "ready": True,
            "directions_passed": directions,
            "validated_check_ids": [check["id"] for check in live["checks"] if check["passed"]],
            "validation_configuration_hash": live["configuration_hash"],
            "validated_at": datetime.now(timezone.utc).isoformat(),
        }
    progress[f"step_{step}"] = values
    progress["last_saved_at"] = datetime.now(timezone.utc).isoformat()
    repository.save_system_setup_state(status="in_progress", current_step=step,
                                       progress_json=json.dumps(progress, sort_keys=True))
    return status_payload()


def record_direction_observation(expected: str, observed: str) -> dict[str, Any]:
    """Persist server-verified direction progress; two consecutive matches pass one cue."""
    expected = expected.upper(); observed = observed.upper()
    if expected not in DIRECTION_SEQUENCE:
        raise ValueError("Unknown direction cue")
    item = repository.get_system_setup_state()
    progress = _progress(item)
    values = dict(progress.get("step_5", {}))
    passed = list(values.get("directions_passed") or [])
    next_expected = DIRECTION_SEQUENCE[len(passed)] if len(passed) < len(DIRECTION_SEQUENCE) else None
    if next_expected is None:
        return status_payload()
    if expected != next_expected:
        raise ValueError(f"Expected the next cue to be {next_expected}")
    stable = int(values.get("direction_stable_count", 0)) + 1 if observed == expected else 0
    values.update(direction_expected=expected, direction_observed=observed,
                  direction_stable_count=stable)
    if stable >= 2:
        passed.append(expected)
        values.update(directions_passed=passed, direction_stable_count=0,
                      direction_verified_at=datetime.now(timezone.utc).isoformat())
    progress["step_5"] = values
    progress["last_saved_at"] = datetime.now(timezone.utc).isoformat()
    repository.save_system_setup_state(status="in_progress", current_step=5,
                                       progress_json=json.dumps(progress, sort_keys=True))
    return status_payload()


def invalidate_direction_progress() -> None:
    """A new eye/head baseline invalidates previously verified directions."""
    item = repository.get_system_setup_state()
    if item is None:
        return
    progress = _progress(item)
    values = dict(progress.get("step_5", {}))
    values.update(ready=False, directions_passed=[], direction_stable_count=0,
                  invalidated_at=datetime.now(timezone.utc).isoformat())
    progress["step_5"] = values
    repository.save_system_setup_state(status="in_progress", current_step=5,
                                       progress_json=json.dumps(progress, sort_keys=True))


def complete_setup(user_id: int | None, user_name: str) -> dict[str, Any]:
    item = repository.get_system_setup_state()
    # Make repeated/double submissions idempotent. A completed, unchanged setup
    # must not create another accepted calibration profile.
    if (item and item.status == "ready" and item.completed_at
            and item.configuration_hash == configuration_hash()):
        return status_payload()
    progress = _progress(item)
    required_manual = progress.get("step_4", {})
    required_keys = {"lighting", "face_framing", "body_framing", "distance"}
    if not all(required_manual.get(key) is True for key in required_keys):
        raise ValueError("Confirm lighting, face framing, body framing, and distance before finishing")
    completion = _step_completion(progress)
    if not completion["5"]:
        raise ValueError("Complete eye, neutral-head, and UP/DOWN/LEFT/RIGHT/CENTER direction checks")
    if not completion["6"]:
        raise ValueError("Test the participant screen and review connectivity before finishing")
    live = readiness()
    failed_checks = [
        check for check in live["checks"]
        if check["id"] in CRITICAL_READINESS and not check["passed"]
    ]
    if failed_checks:
        failed = ", ".join(check["label"] for check in failed_checks)
        raise ValueError(f"Complete system calibration before finishing: {failed}")
    now = datetime.now(timezone.utc)
    manual_checks = {
        "face_visible": bool(required_manual.get("face_framing")),
        "distance_ok": bool(required_manual.get("distance")),
        "body_visible": bool(required_manual.get("body_framing")),
        "lighting_ok": bool(required_manual.get("lighting")),
    }
    profile = create_profile("Guided system setup", None, manual_checks,
                             "Accepted through the unified guided setup workflow.",
                             profile_type="system", created_by_user_id=user_id)
    profile = repository.accept_calibration_profile(profile.id)
    repository.save_system_setup_state(
        status="ready", current_step=STEP_COUNT, progress_json=json.dumps(progress, sort_keys=True),
        configuration_hash=configuration_hash(), calibration_version=f"{SCHEMA_VERSION} · profile {profile.id}",
        completed_by_user_id=user_id, completed_by_name=user_name, completed_at=now,
    )
    return status_payload()


def reset_setup() -> dict[str, Any]:
    repository.save_system_setup_state(status="setup_required", current_step=1,
                                       progress_json="{}", clear_completion=True)
    return status_payload()
