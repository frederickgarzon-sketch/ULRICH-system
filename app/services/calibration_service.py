"""Calibration readiness, immutable snapshots, and safe profile serialization."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.camera.camera_system import camera_system
from app.config import settings
from app.database.repository import repository
from app.services.body_analysis_service import body_analysis_service
from app.services.face_analysis_service import face_analysis_service
from app.services.landmark_config import snapshot as landmark_snapshot

SCHEMA_VERSION = "calibration-1.1-strict"


def summarize_missing_joints(names: list[str]) -> str:
    """Keep placement feedback exact while grouping symmetric left/right joints."""
    remaining = {str(name) for name in names}
    summary: list[str] = []
    if "nose" in remaining:
        summary.append("face/nose")
        remaining.remove("nose")
    for region in ("shoulder", "elbow", "wrist", "hip", "knee", "ankle"):
        left, right = f"left {region}", f"right {region}"
        if left in remaining and right in remaining:
            summary.append(f"both {region}s")
            remaining.remove(left); remaining.remove(right)
        elif left in remaining:
            summary.append(left); remaining.remove(left)
        elif right in remaining:
            summary.append(right); remaining.remove(right)
    summary.extend(sorted(remaining))
    return ", ".join(summary)


def check_allowed(item: dict[str, Any]) -> bool:
    return bool(item["passed"])


def configuration_snapshot() -> dict[str, Any]:
    cameras = camera_system.status()
    return {
        "schema_version": SCHEMA_VERSION,
        "application_mode": settings.app_mode,
        "camera": {
            "face": cameras["face"], "body": cameras["body"],
            "face_processing_fps": settings.face_process_fps,
            "body_processing_fps": settings.body_process_fps,
        },
        "blink": {"threshold": settings.ear_threshold, "minimum_closed_frames": settings.min_closed_frames,
                  "refractory_seconds": settings.blink_refractory_seconds,
                  "maximum_closed_seconds": settings.max_closed_seconds},
        "head": {"smoothing_alpha": settings.head_pose_smoothing_alpha,
                 "movement_threshold_degrees": settings.head_movement_threshold_degrees,
                 "release_degrees": settings.head_movement_release_degrees},
        "body": {"pose_confidence": settings.pose_confidence,
                 "keypoint_confidence": settings.keypoint_confidence,
                 "movement_threshold": settings.body_movement_threshold,
                 "posture_threshold_degrees": settings.posture_change_threshold_degrees},
        "landmarks": landmark_snapshot(),
        "privacy": {"raw_video_recording": settings.save_raw_video},
    }


def configuration_hash() -> str:
    """Stable fingerprint used to detect camera or analysis setup changes."""
    stable = {
        "schema_version": SCHEMA_VERSION,
        "face_camera_source": settings.face_camera_source,
        "body_camera_source": settings.body_camera_source,
        "face_camera_format": [settings.face_camera_width, settings.face_camera_height, settings.face_camera_fps],
        "body_camera_format": [settings.body_camera_width, settings.body_camera_height, settings.body_camera_fps],
        "face_processing_fps": settings.face_process_fps,
        "body_processing_fps": settings.body_process_fps,
        "ear_threshold": settings.ear_threshold,
        "minimum_closed_frames": settings.min_closed_frames,
        "maximum_closed_seconds": settings.max_closed_seconds,
        "blink_refractory_seconds": settings.blink_refractory_seconds,
        "head_smoothing": settings.head_pose_smoothing_alpha,
        "head_movement_threshold_degrees": settings.head_movement_threshold_degrees,
        "head_movement_release_degrees": settings.head_movement_release_degrees,
        "head_event_refractory_seconds": settings.head_movement_refractory_seconds,
        "body_movement_threshold": settings.body_movement_threshold,
        "body_movement_release": settings.body_movement_release,
        "body_movement_smoothing": settings.body_movement_smoothing_alpha,
        "body_event_refractory_seconds": settings.body_event_refractory_seconds,
        "pose_model": settings.pose_model,
        "pose_confidence": settings.pose_confidence,
        "keypoint_confidence": settings.keypoint_confidence,
        "posture_threshold_degrees": settings.posture_change_threshold_degrees,
        "raw_video_recording": settings.save_raw_video,
        "landmarks": landmark_snapshot(),
    }
    canonical = json.dumps(stable, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def current_results() -> dict[str, Any]:
    face = face_analysis_service.snapshot()
    body = body_analysis_service.snapshot()
    return {
        "face": {key: face.get(key) for key in (
            "status", "tracking", "average_ear", "threshold", "calibrated", "calibration_status",
            "yaw", "pitch", "roll", "head_calibrated", "head_calibration_status", "processing_fps",
            "inference_ms")},
        "body": {key: body.get(key) for key in (
            "status", "tracking", "person_count", "movement_magnitude", "regional_movement",
            "posture_angle", "body_scale", "processing_fps", "inference_ms", "model_status", "device")},
    }


def readiness() -> dict[str, Any]:
    cameras = camera_system.status(); face = face_analysis_service.snapshot(); body = body_analysis_service.snapshot()
    missing_names = body.get("missing_required_joint_names") or []
    body_detail = "Simulation tracking" if settings.mock_mode else f"{body.get('person_count', 0)} people · {body.get('status')}"
    if settings.mock_mode:
        pass
    elif missing_names:
        body_detail += " · center upper body, rest hands on lap, and hold still for 2 seconds · missing: " + summarize_missing_joints(missing_names)
    elif not body.get("required_joints_visible"):
        body_detail += " · required joints not visible"
    checks = [
        check("face_camera", "Face camera connected", cameras["face"]["status"] in {"CONNECTED", "MOCK"}, cameras["face"]["status"]),
        check("body_camera", "Body camera connected", cameras["body"]["status"] in {"CONNECTED", "MOCK"}, cameras["body"]["status"]),
        check("face_tracking", "Exactly one usable face", settings.mock_mode or bool(face.get("tracking")), str(face.get("status"))),
        check("body_tracking", "Exactly one primary body", settings.mock_mode or (body.get("tracking") and body.get("person_count") == 1 and body.get("required_joints_visible")), body_detail),
        check("face_fps", "Face source at least 10 FPS", settings.mock_mode or float(cameras["face"].get("capture_fps", 0)) >= 10, f"{cameras['face'].get('capture_fps', 0)} FPS"),
        check("body_fps", "Body source at least 8 FPS", settings.mock_mode or float(cameras["body"].get("capture_fps", 0)) >= 8, f"{cameras['body'].get('capture_fps', 0)} FPS"),
        check("face_calibration", "Eye baseline calibrated", settings.mock_mode or bool(face.get("calibrated")), "Simulation ready" if settings.mock_mode else str(face.get("calibration_status"))),
        check("head_calibration", "Neutral head calibrated", settings.mock_mode or bool(face.get("head_calibrated")), "Simulation ready" if settings.mock_mode else str(face.get("head_calibration_status"))),
        check("privacy", "Raw recording disabled", not settings.save_raw_video, "OFF" if not settings.save_raw_video else "ON"),
    ]
    return {"configuration_hash": configuration_hash(),
            "ready": all(check_allowed(item) for item in checks), "passed": sum(item["passed"] for item in checks),
            "total": len(checks), "checks": checks}


def check(identifier: str, label: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"id": identifier, "label": label, "passed": bool(passed), "detail": detail}


def create_profile(name: str, participant_id: int | None, manual_checks: dict[str, bool],
                   notes: str | None, profile_type: str = "participant",
                   created_by_user_id: int | None = None):
    configuration = configuration_snapshot(); results = current_results()
    digest = configuration_hash()
    return repository.create_calibration_profile(
        name=name, participant_id=participant_id, configuration_hash=digest,
        configuration_json=json.dumps(configuration), results_json=json.dumps(results),
        manual_checks_json=json.dumps(manual_checks, sort_keys=True), notes=notes,
        profile_type=profile_type, created_by_user_id=created_by_user_id,
    )


def payload(item, include_details: bool = True) -> dict[str, Any]:
    value = {"id": item.id, "name": item.name, "participant_id": item.participant_id,
             "profile_type": getattr(item, "profile_type", "participant"),
             "created_by_user_id": getattr(item, "created_by_user_id", None),
             "status": item.status, "schema_version": item.schema_version,
             "configuration_hash": item.configuration_hash, "notes": item.notes,
             "created_at": item.created_at.isoformat(),
             "accepted_at": item.accepted_at.isoformat() if item.accepted_at else None}
    if include_details:
        value.update({"configuration": json.loads(item.configuration_json),
                      "results": json.loads(item.results_json),
                      "manual_checks": json.loads(item.manual_checks_json)})
    return value


def accepted_snapshot(participant_id: int | None) -> dict[str, Any] | None:
    item = repository.latest_accepted_calibration(participant_id)
    return payload(item) if item else None
