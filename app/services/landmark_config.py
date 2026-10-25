"""Versioned landmark-group configuration for lightweight post-processing."""

from __future__ import annotations

import hashlib
import json

from app.config import settings

SCHEMA_VERSION = "landmarks-1.0"
FACE_GROUPS = {"eyes", "iris", "head_pose", "mouth", "face_contour"}
FACE_MEASURE_GROUPS = {"eyes", "head_pose"}
FACE_OVERLAY_ONLY_GROUPS = FACE_GROUPS - FACE_MEASURE_GROUPS
BODY_GROUPS = {"head_shoulders", "left_arm", "right_arm", "torso", "left_leg", "right_leg"}
FEATURE_TYPES = {"position", "distance", "angle", "velocity", "frequency", "normalized_movement"}
PROFILES = {
    "core_monitoring": {
        "face": {"eyes", "head_pose"}, "body": {"head_shoulders", "torso"},
        "features": {"angle", "frequency", "normalized_movement"},
    },
    "upper_body": {
        "face": {"eyes", "head_pose"},
        "body": {"head_shoulders", "left_arm", "right_arm", "torso"},
        "features": {"position", "angle", "velocity", "frequency", "normalized_movement"},
    },
    "full_body": {
        "face": {"eyes", "head_pose"}, "body": set(BODY_GROUPS),
        "features": {"position", "distance", "angle", "velocity", "frequency", "normalized_movement"},
    },
}


def parse_groups(value: str) -> set[str]:
    return settings.csv_set(value)


def snapshot() -> dict[str, object]:
    data = {
        "schema_version": SCHEMA_VERSION,
        "profile": settings.landmark_profile,
        "face_display_groups": sorted(parse_groups(settings.face_display_groups)),
        "face_measure_groups": sorted(parse_groups(settings.face_measure_groups)),
        "body_display_groups": sorted(parse_groups(settings.body_display_groups)),
        "body_measure_groups": sorted(parse_groups(settings.body_measure_groups)),
        "feature_types": sorted(parse_groups(settings.feature_types)),
        "fixed_feature_order": True,
        "availability_mask": True,
    }
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    data["configuration_hash"] = hashlib.sha256(canonical.encode()).hexdigest()[:16]
    return data


def validate_selection(face_display: str, face_measure: str, body_display: str,
                       body_measure: str, feature_types: str) -> None:
    selections = (
        ("face display", parse_groups(face_display), FACE_GROUPS),
        ("face measure", parse_groups(face_measure), FACE_GROUPS),
        ("body display", parse_groups(body_display), BODY_GROUPS),
        ("body measure", parse_groups(body_measure), BODY_GROUPS),
        ("feature types", parse_groups(feature_types), FEATURE_TYPES),
    )
    for label, selected, allowed in selections:
        unknown = selected - allowed
        if unknown:
            raise ValueError(f"Unknown {label}: {', '.join(sorted(unknown))}")
    measured_face = parse_groups(face_measure)
    measured_body = parse_groups(body_measure)
    features = parse_groups(feature_types)
    unsupported_measurements = measured_face - FACE_MEASURE_GROUPS
    if unsupported_measurements:
        raise ValueError(
            "Display-only face groups cannot be measured: "
            + ", ".join(sorted(unsupported_measurements))
        )
    if not measured_face and not measured_body:
        raise ValueError("Select at least one face or body measurement group")
    if "angle" in features and "head_pose" not in measured_face and not ({"head_shoulders", "torso", "left_arm", "right_arm", "left_leg", "right_leg"} & measured_body):
        raise ValueError("Angle requires Head Pose or a body joint group")
    if "normalized_movement" in features and not measured_body:
        raise ValueError("Normalized movement requires at least one body measurement group")
