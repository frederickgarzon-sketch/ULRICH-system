"""Explainable real-time quality indicators for camera and AI pipelines."""

from __future__ import annotations

from typing import Any


def evaluate_pipeline(role: str, camera: dict[str, Any], analysis: dict[str, Any], *, mock: bool = False) -> dict[str, Any]:
    if mock:
        return {"level": "green", "label": "DEMO HEALTHY", "reason": "Synthetic source", "issues": []}
    status = str(camera.get("status", "UNKNOWN")); fps = float(camera.get("capture_fps") or 0)
    latency = float(camera.get("frame_latency_ms") or 0); inference = float(analysis.get("inference_ms") or 0)
    red: list[str] = []; yellow: list[str] = []
    if status != "CONNECTED": red.append(f"Camera {status.lower()}")
    if fps < 5: red.append(f"Capture critically low ({fps:g} FPS)")
    elif fps < (15 if role == "face" else 10): yellow.append(f"Capture below target ({fps:g} FPS)")
    if latency > 750: red.append(f"Stale video ({latency:g} ms)")
    elif latency > 250: yellow.append(f"High video latency ({latency:g} ms)")
    if inference > 750: red.append(f"AI inference stalled ({inference:g} ms)")
    elif inference > (150 if role == "face" else 250): yellow.append(f"Slow AI inference ({inference:g} ms)")
    tracking = bool(analysis.get("tracking"))
    if role == "face" and status == "CONNECTED" and not tracking: yellow.append("Face not currently tracked")
    if role == "body":
        people = int(analysis.get("person_count") or 0)
        if people > 1: red.append(f"Multiple people detected ({people})")
        elif status == "CONNECTED" and (not tracking or people == 0): yellow.append("Body not currently tracked")
    issues = red + yellow; level = "red" if red else "yellow" if yellow else "green"
    labels = {"green": "HEALTHY", "yellow": "CHECK", "red": "NOT READY"}
    return {"level": level, "label": labels[level], "reason": issues[0] if issues else "Real-time quality within target",
            "issues": issues, "metrics": {"capture_fps": fps, "latency_ms": latency, "inference_ms": inference}}
