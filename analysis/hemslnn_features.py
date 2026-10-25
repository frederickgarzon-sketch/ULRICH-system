"""Extract descriptive session features and an optional experimental composite.

The composite produced here is a research aid, not an ADHD diagnosis.  It is
withheld unless a sufficiently large, age-matched reference file is present.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Iterable, Mapping


REFERENCE_MINIMUM = 30
REFERENCE_FILE = Path(__file__).resolve().parents[1] / "data" / "research_reference_features.csv"
REFERENCE_METADATA_FILE = REFERENCE_FILE.with_name("research_reference_metadata.json")
FEATURE_KEYS = (
    "omission_rate",
    "commission_rate",
    "rt_cv",
    "attention_span_s",
    "blink_delta",
    "body_mean_task",
    "head_speed_deg_s",
)
INDICATOR_WEIGHTS = {"body": 0.30, "head": 0.25, "attention": 0.25, "blink": 0.20}


def _number(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _mean(values: Iterable[object]) -> float | None:
    clean = [number for value in values if (number := _number(value)) is not None]
    return statistics.fmean(clean) if clean else None


def _rate(count: int, seconds: float) -> float | None:
    return count * 60.0 / seconds if seconds > 0 else None


def _longest_correct_run(trials: list[Mapping[str, object]]) -> int:
    longest = current = 0
    for trial in trials:
        if bool(trial.get("correct")):
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _trial_step_seconds(trials: list[Mapping[str, object]], report: Mapping[str, object]) -> float:
    times = sorted(number for item in trials if (number := _number(item.get("time"))) is not None)
    differences = [later - earlier for earlier, later in zip(times, times[1:]) if later > earlier]
    if differences:
        return statistics.median(differences)
    configurations = report.get("attention_configuration") or []
    if configurations:
        configuration = configurations[0].get("configuration") or {}
        display = _number(configuration.get("display_ms"))
        intertrial = _number(configuration.get("intertrial_ms"))
        if display is not None and intertrial is not None:
            return (display + intertrial) / 1000.0
    return 1.7


def extract(source: Mapping[str, object] | str | Path) -> dict[str, object]:
    """Return one row of descriptive features from a report mapping or session.json."""
    if isinstance(source, (str, Path)):
        path = Path(source)
        path = path / "session.json" if path.is_dir() else path
        report = json.loads(path.read_text(encoding="utf-8"))
    else:
        report = source

    attention = report.get("attention") or {}
    trials = list(attention.get("trials") or [])
    trials = sorted(trials, key=lambda item: (_number(item.get("time")) is None,
                                              _number(item.get("time")) or 0))
    targets = [item for item in trials if bool(item.get("is_target"))]
    non_targets = [item for item in trials if not bool(item.get("is_target"))]
    omission_rate = sum(bool(item.get("missed")) for item in targets) / len(targets) if targets else None
    commission_rate = (sum(bool(item.get("false_response")) for item in non_targets) / len(non_targets)
                       if non_targets else None)
    reaction_times = [number for value in attention.get("reaction_times") or []
                      if (number := _number(value)) is not None]
    rt_mean = statistics.fmean(reaction_times) if reaction_times else None
    rt_cv = (statistics.pstdev(reaction_times) / rt_mean
             if len(reaction_times) > 1 and rt_mean and rt_mean > 0 else None)
    step_seconds = _trial_step_seconds(trials, report)
    attention_span_s = _longest_correct_run(trials) * step_seconds if trials else None

    phase_events = list(report.get("phases") or [])
    task_markers = [value for item in phase_events if item.get("phase") == "task"
                    and (value := _number(item.get("time"))) is not None]
    post_markers = [value for item in phase_events if item.get("phase") == "post_task"
                    and (value := _number(item.get("time"))) is not None]
    trial_times = [number for item in trials if (number := _number(item.get("time"))) is not None]
    task_start = min(task_markers) if task_markers else (min(trial_times) if trial_times else None)
    task_end = min(post_markers) if post_markers else (max(trial_times) + step_seconds if trial_times else None)
    session_duration = _number((report.get("session") or {}).get("duration_seconds"))
    if task_start is not None and task_end is not None and session_duration is not None:
        task_end = min(task_end, session_duration)

    blink_events = list((report.get("blink") or {}).get("events") or [])
    blink_delta = baseline_rate = task_rate = None
    if task_start is not None and task_end is not None and task_start > 0 and task_end > task_start:
        baseline_count = sum(1 for item in blink_events if item.get("phase") == "baseline")
        task_count = sum(1 for item in blink_events if item.get("phase") == "task")
        if not any(item.get("phase") for item in blink_events):
            baseline_count = sum(1 for item in blink_events
                                 if (time := _number(item.get("time"))) is not None and 0 <= time < task_start)
            task_count = sum(1 for item in blink_events
                             if (time := _number(item.get("time"))) is not None and task_start <= time <= task_end)
        baseline_rate = _rate(baseline_count, task_start)
        task_rate = _rate(task_count, task_end - task_start)
        if baseline_rate is not None and task_rate is not None:
            blink_delta = task_rate - baseline_rate

    body_samples = list((report.get("body") or {}).get("samples") or [])
    body_task = [item.get("magnitude") for item in body_samples if item.get("phase") == "task" and item.get("valid", True)]
    if not any(item.get("phase") for item in body_samples):
        body_task = [item.get("magnitude") for item in body_samples
                     if task_start is not None and task_end is not None
                     and (time := _number(item.get("time"))) is not None and task_start <= time <= task_end]
    body_mean_task = _mean(body_task)

    head_samples = list((report.get("head") or {}).get("samples") or [])
    valid_head = [item for item in head_samples
                  if all(_number(item.get(axis)) is not None for axis in ("yaw", "pitch", "roll"))]
    head_task = [item for item in valid_head if item.get("phase") == "task"]
    if not any(item.get("phase") for item in head_samples):
        head_task = [item for item in valid_head
                     if task_start is not None and task_end is not None
                     and (time := _number(item.get("time"))) is not None and task_start <= time <= task_end]
    speeds: list[float] = []
    for previous, current in zip(head_task, head_task[1:]):
        elapsed = (_number(current.get("time")) or 0) - (_number(previous.get("time")) or 0)
        if elapsed <= 0:
            continue
        delta = math.sqrt(sum(((_number(current.get(axis)) or 0) -
                               (_number(previous.get(axis)) or 0)) ** 2
                              for axis in ("yaw", "pitch", "roll")))
        speeds.append(delta / elapsed)

    age_group = (report.get("participant") or {}).get("age_group")
    return {
        "age_group": age_group,
        "n_trials": len(trials),
        "n_targets": len(targets),
        "omission_rate": omission_rate,
        "commission_rate": commission_rate,
        "rt_cv": rt_cv,
        "attention_span_s": attention_span_s,
        "blink_rate_baseline": baseline_rate,
        "blink_rate_task": task_rate,
        "blink_delta": blink_delta,
        "body_mean_task": body_mean_task,
        "head_speed_deg_s": _mean(speeds),
        "task_start_s": task_start,
        "task_end_s": task_end,
        "head_valid_pct": round(len(valid_head) * 100 / len(head_samples), 1) if head_samples else 0.0,
    }


def load_reference_rows(path: str | Path = REFERENCE_FILE) -> list[dict[str, object]]:
    reference_path = Path(path)
    if not reference_path.exists():
        return []
    with reference_path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def load_reference_provenance(path: str | Path = REFERENCE_METADATA_FILE) -> dict[str, object] | None:
    metadata_path = Path(path)
    if not metadata_path.exists():
        return None
    try:
        value = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    required = ("version", "cohort", "source", "approval_reference", "sha256", "imported_at")
    if not isinstance(value, dict) or not all(value.get(key) for key in required):
        return None
    if REFERENCE_FILE.exists() and hashlib.sha256(REFERENCE_FILE.read_bytes()).hexdigest() != value.get("sha256"):
        return None
    return value


def score(features: Mapping[str, object], reference_rows: Iterable[Mapping[str, object]] | None = None,
          *, minimum_reference_size: int = REFERENCE_MINIMUM) -> dict[str, object]:
    """Calculate provisional z-scores only with an adequate age-matched reference."""
    supplied_rows = reference_rows is not None
    provenance = None if supplied_rows else load_reference_provenance()
    rows = list(reference_rows if supplied_rows else load_reference_rows())
    if not supplied_rows and provenance is None:
        return {
            "status": "reference_required", "score": None,
            "interpretation": "Approved, integrity-verified reference data required",
            "reference_count": 0, "minimum_reference_count": minimum_reference_size,
            "indicators_used": 0, "z_scores": {}, "reference_provenance": None,
        }
    age_group = features.get("age_group")
    if age_group:
        rows = [row for row in rows if row.get("age_group") == age_group]
    if len(rows) < minimum_reference_size:
        return {
            "status": "reference_required",
            "score": None,
            "interpretation": "Reference data required",
            "reference_count": len(rows),
            "minimum_reference_count": minimum_reference_size,
            "indicators_used": 0,
            "z_scores": {},
            "reference_provenance": provenance,
        }

    z_scores: dict[str, float] = {}
    for key in FEATURE_KEYS:
        value = _number(features.get(key))
        reference = [number for row in rows if (number := _number(row.get(key))) is not None]
        if value is None or len(reference) < minimum_reference_size:
            continue
        deviation = statistics.stdev(reference)
        if deviation <= 1e-12:
            continue
        z_scores[key] = (value - statistics.fmean(reference)) / deviation

    attention_parts = [z_scores[key] * (-1 if key == "attention_span_s" else 1)
                       for key in ("omission_rate", "commission_rate", "rt_cv", "attention_span_s")
                       if key in z_scores]
    indicators = {
        "body": z_scores.get("body_mean_task"),
        "head": z_scores.get("head_speed_deg_s"),
        "attention": statistics.fmean(attention_parts) if len(attention_parts) >= 3 else None,
        "blink": z_scores.get("blink_delta"),
    }
    available = {key: value for key, value in indicators.items() if value is not None}
    if len(available) < 3:
        return {
            "status": "insufficient_signals",
            "score": None,
            "interpretation": "Inconclusive — repeat or review missing signals",
            "reference_count": len(rows),
            "minimum_reference_count": minimum_reference_size,
            "indicators_used": len(available),
            "z_scores": {key: round(value, 3) for key, value in z_scores.items()},
            "indicator_z": {key: round(value, 3) for key, value in available.items()},
            "reference_provenance": provenance,
        }
    weight_total = sum(INDICATOR_WEIGHTS[key] for key in available)
    composite = sum(INDICATOR_WEIGHTS[key] * value for key, value in available.items()) / weight_total
    return {
        "status": "experimental_only",
        "score": round(composite, 3),
        "interpretation": "Research review suggested" if composite >= 1.0 else "No marked composite elevation",
        "reference_count": len(rows),
        "minimum_reference_count": minimum_reference_size,
        "indicators_used": len(available),
        "z_scores": {key: round(value, 3) for key, value in z_scores.items()},
        "indicator_z": {key: round(value, 3) for key, value in available.items()},
        "reference_provenance": provenance,
    }


def screening_summary(report: Mapping[str, object]) -> dict[str, object]:
    features = extract(report)
    result = score(features)
    return {
        **result,
        "name": "Experimental Behavioral Indicator",
        "version": "research-0.1",
        "clinically_validated": False,
        "features": features,
        "notice": ("Research-use composite only. These measurements are not, by themselves, "
                   "a diagnosis of ADHD."),
    }
