"""Monocular face-camera distance estimate for placement guidance only."""
import math
from typing import Sequence

def estimate_face_distance_cm(left_eye: Sequence[tuple[float, float]], right_eye: Sequence[tuple[float, float]], width: int, height: int, *, horizontal_fov_degrees: float = 60.0, reference_ipd_cm: float = 6.3) -> float | None:
    if not left_eye or not right_eye or width <= 0 or height <= 0 or not 20 < horizontal_fov_degrees < 140: return None
    lx=sum(p[0] for p in left_eye)/len(left_eye)*width; ly=sum(p[1] for p in left_eye)/len(left_eye)*height
    rx=sum(p[0] for p in right_eye)/len(right_eye)*width; ry=sum(p[1] for p in right_eye)/len(right_eye)*height
    eye_pixels=math.hypot(rx-lx,ry-ly)
    if eye_pixels < 2: return None
    focal_pixels=width/(2*math.tan(math.radians(horizontal_fov_degrees)/2))
    return round(reference_ipd_cm*focal_pixels/eye_pixels,1)

def distance_quality(distance_cm: float | None) -> tuple[str,str]:
    if distance_cm is None:return "red","Distance unavailable — keep both eyes visible"
    if distance_cm < 25:return "red","Too close — move back"
    if distance_cm < 35:return "yellow","A little close — move back"
    if distance_cm <= 45:return "green","Correct distance — hold position"
    if distance_cm <= 60:return "yellow","A little far — move closer"
    return "red","Too far — move closer"
