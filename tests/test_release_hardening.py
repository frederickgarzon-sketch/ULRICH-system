import csv
import io
import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

from app.services import reference_data_service, system_setup_service
from app.services.export_service import database_backup_archive
from app.database.database import initialize_database
from scripts.restore_backup import restore


def test_normal_launcher_does_not_log_participant_pairing_tokens():
    launcher = (Path(__file__).resolve().parents[1] / "run.py").read_text(encoding="utf-8")
    assert "access_log=False" in launcher


def reference_csv(rows: int = 30) -> bytes:
    output = io.StringIO(newline="")
    fields = list(reference_data_service.REQUIRED_COLUMNS)
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for index in range(rows):
        writer.writerow({"age_group": "child", **{key: index / 100 for key in fields[1:]}})
    return output.getvalue().encode("utf-8")


def test_reference_import_records_provenance_and_integrity(tmp_path, monkeypatch):
    data = tmp_path / "reference.csv"
    metadata = tmp_path / "metadata.json"
    monkeypatch.setattr(reference_data_service, "REFERENCE_FILE", data)
    monkeypatch.setattr(reference_data_service, "METADATA_FILE", metadata)
    result = reference_data_service.import_csv(
        reference_csv(), version="v1", cohort="Age-matched research cohort",
        source="Study custodian", approval_reference="IRB-001", imported_by="Owner",
    )
    saved = json.loads(metadata.read_text(encoding="utf-8"))
    assert result["rows"] == 30
    assert result["eligible_age_groups"] == ["child"]
    assert saved["version"] == "v1" and saved["approval_reference"] == "IRB-001"
    assert len(saved["sha256"]) == 64
    assert result["clinically_validated"] is False


def test_reference_import_rejects_missing_governance(tmp_path, monkeypatch):
    monkeypatch.setattr(reference_data_service, "REFERENCE_FILE", tmp_path / "reference.csv")
    monkeypatch.setattr(reference_data_service, "METADATA_FILE", tmp_path / "metadata.json")
    with pytest.raises(ValueError, match="approval"):
        reference_data_service.import_csv(reference_csv(), version="v1", cohort="cohort",
                                          source="source", approval_reference="", imported_by="Owner")


def test_backup_restore_drill_uses_verified_archive_and_safety_copy(tmp_path):
    archive = tmp_path / "backup.zip"
    archive.write_bytes(database_backup_archive())
    target = tmp_path / "restored.db"
    target.write_bytes(b"old database placeholder")
    result = restore(archive, target, confirm=True)
    assert result["valid"] is True
    assert result["safety_copy"]
    connection = sqlite3.connect(target)
    try:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        connection.close()


def test_recalibration_invalidates_saved_directions():
    initialize_database()
    system_setup_service.reset_setup()
    for direction in ("UP", "DOWN", "LEFT", "RIGHT", "CENTER"):
        system_setup_service.record_direction_observation(direction, direction)
        system_setup_service.record_direction_observation(direction, direction)
    system_setup_service.save_progress(5, {"ready": True})
    system_setup_service.invalidate_direction_progress()
    progress = system_setup_service.status_payload()["progress"]["step_5"]
    assert progress["ready"] is False
    assert progress["directions_passed"] == []
