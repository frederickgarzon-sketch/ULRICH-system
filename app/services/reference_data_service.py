"""Validated, auditable management of optional research reference cohorts."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analysis.hemslnn_features import FEATURE_KEYS, REFERENCE_FILE, REFERENCE_MINIMUM

METADATA_FILE = REFERENCE_FILE.with_name("research_reference_metadata.json")
REQUIRED_COLUMNS = ("age_group", *FEATURE_KEYS)


def status() -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    if METADATA_FILE.exists():
        try:
            metadata = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            metadata = {"warning": "Reference metadata is unreadable"}
    counts: Counter[str] = Counter()
    rows = 0
    if REFERENCE_FILE.exists():
        with REFERENCE_FILE.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                rows += 1
                counts[str(row.get("age_group") or "unspecified")] += 1
    eligible = sorted(group for group, count in counts.items() if count >= REFERENCE_MINIMUM)
    return {"installed": REFERENCE_FILE.exists(), "rows": rows, "age_group_counts": dict(counts),
            "eligible_age_groups": eligible, "minimum_per_age_group": REFERENCE_MINIMUM,
            "metadata": metadata, "clinically_validated": False,
            "notice": "Research reference only; it does not establish diagnostic validity."}


def import_csv(content: bytes, *, version: str, cohort: str, source: str,
               approval_reference: str, imported_by: str) -> dict[str, Any]:
    if not all(value.strip() for value in (version, cohort, source, approval_reference)):
        raise ValueError("Version, cohort description, source, and approval reference are required")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Reference CSV must be UTF-8 encoded") from exc
    reader = csv.DictReader(io.StringIO(text))
    missing = [column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or [])]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    rows = list(reader)
    if not rows:
        raise ValueError("Reference CSV has no data rows")
    for number, row in enumerate(rows, start=2):
        if not str(row.get("age_group") or "").strip():
            raise ValueError(f"Row {number}: age_group is required")
        for key in FEATURE_KEYS:
            value = str(row.get(key) or "").strip()
            if value:
                try:
                    float(value)
                except ValueError as exc:
                    raise ValueError(f"Row {number}: {key} must be numeric or blank") from exc
    digest = hashlib.sha256(content).hexdigest()
    metadata = {"version": version.strip(), "cohort": cohort.strip(), "source": source.strip(),
                "approval_reference": approval_reference.strip(), "sha256": digest,
                "row_count": len(rows), "imported_by": imported_by,
                "imported_at": datetime.now(timezone.utc).isoformat(),
                "clinically_validated": False}
    REFERENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(REFERENCE_FILE, content)
    _atomic_write(METADATA_FILE, json.dumps(metadata, indent=2, sort_keys=True).encode("utf-8"))
    return status()


def _atomic_write(path: Path, content: bytes) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
