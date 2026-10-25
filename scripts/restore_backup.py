"""Verify and restore a database-backup ZIP while the server is stopped.

The existing database is first copied to a timestamped sibling backup. This
script never targets a directory and requires an explicit --confirm flag.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

try:
    from verify_backup import verify
except ModuleNotFoundError:  # Imported as scripts.restore_backup in tests.
    from scripts.verify_backup import verify


def restore(archive_path: Path, target: Path, *, confirm: bool = False) -> dict[str, object]:
    if not confirm:
        raise ValueError("Pass --confirm after stopping the Behavior Monitor server")
    result = verify(archive_path.resolve())
    target = target.resolve()
    if target.suffix.lower() not in {".db", ".sqlite", ".sqlite3"}:
        raise ValueError("Restore target must be a SQLite database file")
    target.parent.mkdir(parents=True, exist_ok=True)
    safety_copy = None
    if target.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safety_copy = target.with_name(f"{target.stem}.before-restore-{stamp}{target.suffix}")
        shutil.copy2(target, safety_copy)
    with tempfile.TemporaryDirectory(dir=target.parent) as directory:
        staged = Path(directory) / target.name
        with zipfile.ZipFile(archive_path) as archive:
            staged.write_bytes(archive.read("behavioral_monitoring.db"))
        connection = sqlite3.connect(staged)
        try:
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Staged database failed SQLite integrity check")
        finally:
            connection.close()
        staged.replace(target)
    return {**result, "restored_to": str(target),
            "safety_copy": str(safety_copy) if safety_copy else None}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", type=Path)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--confirm", action="store_true")
    arguments = parser.parse_args()
    result = restore(arguments.backup, arguments.target, confirm=arguments.confirm)
    print(result)


if __name__ == "__main__":
    main()
