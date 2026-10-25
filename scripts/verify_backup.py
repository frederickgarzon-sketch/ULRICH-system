"""Verify a Behavior Monitor database-backup ZIP without modifying live data."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import tempfile
import zipfile
from pathlib import Path


def verify(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise ValueError(f"Backup not found: {path}")
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        required = {"behavioral_monitoring.db", "manifest.json"}
        if not required <= names:
            raise ValueError("Backup is missing the database or manifest")
        manifest = json.loads(archive.read("manifest.json"))
        database_bytes = archive.read("behavioral_monitoring.db")
    expected = manifest.get("sha256")
    actual = hashlib.sha256(database_bytes).hexdigest()
    if expected != actual:
        raise ValueError("Database SHA-256 does not match the backup manifest")
    with tempfile.TemporaryDirectory() as directory:
        database_path = Path(directory) / "verify.db"
        database_path.write_bytes(database_bytes)
        connection = sqlite3.connect(database_path)
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            tables = connection.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchone()[0]
        finally:
            connection.close()
    if integrity != "ok":
        raise ValueError(f"SQLite integrity check failed: {integrity}")
    return {"valid": True, "sha256": actual, "bytes": len(database_bytes),
            "tables": tables, "schema_version": manifest.get("schema_version")}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", type=Path, help="Path to database-backup-*.zip")
    result = verify(parser.parse_args().backup)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
