from pathlib import Path

from app.services.export_service import database_backup_archive
from scripts.verify_backup import verify


def test_generated_database_backup_passes_restore_verification(tmp_path: Path) -> None:
    backup = tmp_path / "backup.zip"
    backup.write_bytes(database_backup_archive())
    result = verify(backup)
    assert result["valid"] is True
    assert result["tables"] > 0
    assert len(result["sha256"]) == 64
