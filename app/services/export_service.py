"""Research-data exports with machine-readable integrity metadata."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from app.database.database import engine
from app.database.repository import repository


EXPORT_SCHEMA_VERSION = "2.1"


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8")


def _csv_bytes(columns: list[str], rows: list[dict[str, object]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8-sig")


def session_json(session_id: int) -> bytes | None:
    report = repository.build_report(session_id)
    if report is None:
        return None
    return _json_bytes({"schema_version": EXPORT_SCHEMA_VERSION, "exported_at": _now(), **report})


def session_archive(session_id: int) -> bytes | None:
    report = repository.build_report(session_id)
    if report is None:
        return None

    files: dict[str, bytes] = {
        "shape_matching_trials.csv": _csv_bytes(
            ["run_id", "game_type", "trial", "shape", "outcome", "active_ms", "wrong_drops", "first_attempt_correct"],
            [{"run_id": run["id"], "game_type": "shape_matching", **row}
             for run in report.get("shape_matching", []) for row in run["rows"]]),
        "session.json": _json_bytes({"schema_version": EXPORT_SCHEMA_VERSION, "exported_at": _now(), **report}),
        "blink_events.csv": _csv_bytes(["time", "ear", "closure_duration_seconds", "phase"], report["blink"]["events"]),
        "head_pose_samples.csv": _csv_bytes(["time", "yaw", "pitch", "roll", "valid", "status", "phase"], report["head"]["samples"]),
        "head_movement_events.csv": _csv_bytes(
            ["time", "direction", "magnitude", "phase"], report["head"]["events"]
        ),
        "body_movement_samples.csv": _csv_bytes(["time", "magnitude", "valid", "status", "phase"], report["body"]["samples"]),
        "body_movement_events.csv": _csv_bytes(["time", "magnitude", "phase"], report["body"]["events"]),
        "posture_events.csv": _csv_bytes(["time", "angle", "phase"], report["body"]["posture_events"]),
        "attention_trials.csv": _csv_bytes(
            ["trial", "stimulus", "time", "reaction_time_ms", "is_target", "responded",
             "correct", "missed", "false_response", "premature_taps", "phase", "balloon_color",
             "target_color", "x_percent", "y_percent", "size_px", "speed", "display_ms",
             "intertrial_ms", "face_valid", "body_valid", "pause_context"],
            [{**trial,
              "balloon_color": (trial.get("balloon") or {}).get("color"),
              "target_color": (trial.get("balloon") or {}).get("target_color"),
              "x_percent": (trial.get("balloon") or {}).get("x_percent"),
              "y_percent": (trial.get("balloon") or {}).get("y_percent"),
              "size_px": (trial.get("balloon") or {}).get("size_px"),
              "speed": (trial.get("balloon") or {}).get("speed"),
              "display_ms": (trial.get("balloon") or {}).get("display_ms"),
              "intertrial_ms": (trial.get("balloon") or {}).get("intertrial_ms"),
              "face_valid": ((trial.get("balloon") or {}).get("tracking") or {}).get("face_valid"),
              "body_valid": ((trial.get("balloon") or {}).get("tracking") or {}).get("body_valid"),
              "pause_context": (trial.get("balloon") or {}).get("pause_context")}
             for trial in report["attention"]["trials"]],
        ),
        "tracking_validity.csv": _csv_bytes(
            ["time", "phase", "face_valid", "eyes_valid", "head_valid", "body_valid", "face_status", "body_status"],
            report["data_quality"].get("validity_samples", []),
        ),
        "session_phases.csv": _csv_bytes(["time", "phase", "occurred_at"], report.get("phases", [])),
        "research_features.csv": _csv_bytes(
            list((report.get("research_screening") or {}).get("features", {}).keys()),
            [(report.get("research_screening") or {}).get("features", {})],
        ),
    }
    manifest = {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "exported_at": _now(),
        "session_id": session_id,
        "participant_code": report["session"]["participant_code"],
        "contains_raw_video": False,
        "files": {
            name: {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
            for name, content in files.items()
        },
    }
    files["manifest.json"] = _json_bytes(manifest)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return output.getvalue()


def database_backup_archive() -> bytes:
    if engine.url.get_backend_name() != "sqlite" or not engine.url.database:
        raise RuntimeError("Database backup is currently supported only for SQLite")
    source_path = Path(engine.url.database).resolve()
    with tempfile.TemporaryDirectory() as temp_dir:
        backup_path = Path(temp_dir) / "behavioral_monitoring.db"
        source = sqlite3.connect(source_path)
        destination = sqlite3.connect(backup_path)
        try:
            source.backup(destination)
        finally:
            destination.close()
            source.close()
        database_bytes = backup_path.read_bytes()
    manifest = {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "exported_at": _now(),
        "database": "behavioral_monitoring.db",
        "bytes": len(database_bytes),
        "sha256": hashlib.sha256(database_bytes).hexdigest(),
        "contains_raw_video": False,
        "warning": "Contains research participant and session data. Store securely.",
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("behavioral_monitoring.db", database_bytes)
        archive.writestr("manifest.json", _json_bytes(manifest))
    return output.getvalue()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
