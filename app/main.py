"""FastAPI application factory and web interface."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

import cv2
from fastapi import FastAPI, Form, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes import router
from app.camera.camera_system import camera_system
from app.config import ROOT_DIR, settings
from app.database.database import initialize_database, recover_interrupted_sessions
from app.logging_config import configure_logging
from app.services.mock_monitor import mock_monitor
from app.services.face_analysis_service import face_analysis_service
from app.services.body_analysis_service import body_analysis_service
from app.sessions.session_manager import session_manager
from app.tasks.attention_task import attention_task_service
from app.services.access_control import (ADMIN_UNLOCK_COOKIE, COOKIE_NAME, authenticate_access_key,
                                         configuration_valid, issue_admin_unlock, issue_token,
                                         token_identity, valid_admin_unlock, valid_token)
from app.services.system_setup_service import status_payload as setup_status_payload
from app.database.repository import repository

configure_logging()
logger = logging.getLogger(__name__)
_login_failures: dict[str, deque[float]] = defaultdict(deque)
_login_guard = threading.Lock()
_LOGIN_WINDOW_SECONDS = 300
_LOGIN_FAILURE_LIMIT = 5


def _origin_matches_request(origin: str, request: Request) -> bool:
    """Accept the current origin, including equivalent local loopback aliases."""
    try:
        supplied = urlsplit(origin)
        expected = urlsplit(str(request.base_url))
        supplied_port = supplied.port or (443 if supplied.scheme == "https" else 80)
        expected_port = expected.port or (443 if expected.scheme == "https" else 80)
    except ValueError:
        return False
    if not supplied.scheme or not supplied.hostname:
        return False
    if supplied.scheme == expected.scheme and supplied.hostname == expected.hostname and supplied_port == expected_port:
        return True
    loopback_names = {"localhost", "127.0.0.1", "::1"}
    return (supplied.scheme == expected.scheme and supplied_port == expected_port and
            supplied.hostname in loopback_names and expected.hostname in loopback_names)


@asynccontextmanager
async def lifespan(_: FastAPI):
    (ROOT_DIR / "data").mkdir(exist_ok=True)
    initialize_database()
    if settings.auth_enabled and not configuration_valid():
        raise RuntimeError("AUTH_ENABLED requires RESEARCHER_ACCESS_KEY and a SESSION_SECRET of at least 32 characters")
    recovered = recover_interrupted_sessions()
    if recovered:
        logger.warning("Marked %s previously active session(s) as interrupted", recovered)
    face_analysis_service.restore_saved_calibration()
    camera_system.start()
    face_analysis_service.start()
    body_analysis_service.start()
    logger.info("Database initialized")
    logger.info("Application mode: %s", settings.app_mode)
    yield
    session_manager.shutdown()
    body_analysis_service.stop()
    face_analysis_service.stop()
    camera_system.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router)
app.mount("/static", StaticFiles(directory=ROOT_DIR / "static"), name="static")
templates = Jinja2Templates(directory=ROOT_DIR / "templates")


@app.middleware("http")
async def local_security_headers(request: Request, call_next):
    # Login is intentionally exempt from Origin validation. It has no existing
    # authenticated state to forge, still requires the private access key, and
    # is independently rate-limited. Some local browsers omit or rewrite fetch
    # metadata, which previously made the normal login form return JSON 403.
    if request.method not in {"GET", "HEAD", "OPTIONS"} and request.url.path != "/login":
        fetch_site = request.headers.get("sec-fetch-site", "").lower()
        if fetch_site == "cross-site":
            return JSONResponse(status_code=403, content={"detail": "Cross-site request blocked"})
        origin = request.headers.get("origin")
        # Browsers set Sec-Fetch-Site themselves. A same-origin form submission
        # is safe even when a local proxy/browser reports a mismatched Origin.
        if origin and not _origin_matches_request(origin, request) and fetch_site != "same-origin":
            return JSONResponse(status_code=403, content={"detail": "Request origin is not allowed"})
    content_length = request.headers.get("content-length")
    try:
        oversized = bool(content_length and int(content_length) > 1_000_000)
    except ValueError:
        return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length header"})
    if oversized:
        return JSONResponse(status_code=413, content={"detail": "Request body too large"})
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/") else "no-cache"
    return response


@app.middleware("http")
async def researcher_access(request: Request, call_next):
    if not settings.auth_enabled:
        return await call_next(request)
    path = request.url.path
    public = (path == "/login" or path.startswith("/static/") or path == "/api/health" or
              path == "/attention-task" or (path == "/shape-matching" and bool(request.query_params.get("token"))) or path == "/api/attention/catalog" or
              path.startswith("/api/participant-task/"))
    identity = token_identity(request.cookies.get(COOKIE_NAME))
    request.state.identity = identity
    if public:
        return await call_next(request)
    if identity:
        admin_only = (path.startswith("/users") or path.startswith("/settings") or
                      path.startswith("/system-setup") or
                      path.startswith("/hardware") or
                      path.startswith("/api/users") or path.startswith("/api/settings") or
                      path.startswith("/api/audit") or path.startswith("/api/exports/database-backup"))
        admin_only = admin_only or path.startswith("/api/research-reference")
        if admin_only and identity.role not in {"owner", "admin"}:
            if path.startswith("/api/"):
                return JSONResponse(status_code=403, content={"detail": "Administrator access required"})
            return RedirectResponse("/?access=restricted", status_code=303)
        if identity.role == "reviewer" and request.method not in {"GET", "HEAD", "OPTIONS"}:
            return JSONResponse(status_code=403, content={"detail": "Reviewer access is read-only"})
        setup = setup_status_payload()
        protected_setup_write = (
            path in {"/api/settings", "/api/setup/reset", "/api/setup/progress", "/api/setup/complete",
                     "/api/face/calibration/start", "/api/head/calibration/start", "/api/setup/direction-check",
                     "/api/research-reference/import"}
            or (path.startswith("/api/calibration/profiles") and path != "/api/calibration/verify")
        )
        if (settings.auth_enabled and setup["completed"] and request.method not in {"GET", "HEAD", "OPTIONS"} and
                protected_setup_write and
                not valid_admin_unlock(request.cookies.get(ADMIN_UNLOCK_COOKIE), identity)):
            return JSONResponse(status_code=403, content={"detail": "Confirm the administrator access key in System Setup"})
        operation_pages = {"/", "/live-monitor", "/attention", "/records", "/participants"}
        if request.method == "GET" and path in operation_pages and not setup["can_operate"]:
            return RedirectResponse(f"/setup?step={setup['current_step']}", status_code=303)
        if (request.method == "POST" and path == "/api/sessions/start" and
                not settings.mock_mode and not setup["can_start"]):
            return JSONResponse(status_code=409, content={"detail": setup["message"],
                                                         "repair_url": f"/setup?step={setup['current_step']}"})
        return await call_next(request)
    if path.startswith("/api/") or path.startswith("/preview/"):
        return JSONResponse(status_code=401, content={"detail": "Researcher authentication required"})
    next_path = path if path.startswith("/") and not path.startswith("//") else "/"
    return RedirectResponse(f"/login?next={next_path}", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str = "/"):
    if settings.auth_enabled and valid_token(request.cookies.get(COOKIE_NAME)):
        setup = setup_status_payload()
        return RedirectResponse("/" if setup["can_operate"] else f"/setup?step={setup['current_step']}", status_code=303)
    next_path = next if next.startswith("/") and not next.startswith("//") else "/"
    return templates.TemplateResponse(request=request, name="login.html",
                                      context={"app_name": settings.app_name, "error": None,
                                               "next_path": next_path})


@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, access_key: str = Form(...), next: str = Form("/")):
    client_ip = request.client.host if request.client else None
    rate_key = client_ip or "unknown"
    now = time.monotonic()
    with _login_guard:
        failures = _login_failures[rate_key]
        while failures and now - failures[0] > _LOGIN_WINDOW_SECONDS:
            failures.popleft()
        if len(failures) >= _LOGIN_FAILURE_LIMIT:
            repository.add_audit_event("login.rate_limited", "researcher", client_ip, False)
            return templates.TemplateResponse(request=request, name="login.html", status_code=429,
                context={"app_name": settings.app_name,
                         "error": "Too many attempts. Wait five minutes before trying again.",
                         "next_path": "/"})
    next_path = next if next.startswith("/") and not next.startswith("//") else "/"
    identity = authenticate_access_key(access_key)
    if identity is None:
        with _login_guard:
            _login_failures[rate_key].append(now)
        repository.add_audit_event("login", "researcher", client_ip, False, "Invalid access key")
        return templates.TemplateResponse(request=request, name="login.html", status_code=401,
                                          context={"app_name": settings.app_name,
                                                   "error": "Invalid access key.", "next_path": next_path})
    repository.add_audit_event("login", identity.full_name, client_ip, True, f"role={identity.role}")
    with _login_guard:
        _login_failures.pop(rate_key, None)
    setup = setup_status_payload()
    destination = next_path if setup["can_operate"] else f"/setup?step={setup['current_step']}"
    response = RedirectResponse(destination, status_code=303)
    response.set_cookie(COOKIE_NAME, issue_token(identity), max_age=settings.auth_session_hours * 3600,
                        httponly=True, samesite="strict", secure=False, path="/")
    return response


@app.post("/logout")
def logout(request: Request):
    repository.add_audit_event("logout", "researcher", request.client.host if request.client else None)
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(COOKIE_NAME, path="/")
    response.delete_cookie(ADMIN_UNLOCK_COOKIE, path="/")
    return response


def dashboard_response(request: Request, page: str, page_title: str, page_subtitle: str):
    identity = getattr(request.state, "identity", None)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"app_name": settings.app_name, "mock_mode": settings.mock_mode,
                 "page": page, "page_title": page_title, "page_subtitle": page_subtitle,
                 "identity": identity},
    )


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return dashboard_response(request, "overview", "Overview", "Research command center")


@app.get("/live-monitor", response_class=HTMLResponse)
def live_monitor_page(request: Request):
    return dashboard_response(request, "live", "Live monitor", "Camera feeds and behavioral signals")


@app.get("/attention", response_class=HTMLResponse)
def attention_console_page(request: Request):
    return dashboard_response(request, "attention", "Research tasks", "Participant protocols and task workflow")


@app.get("/records", response_class=HTMLResponse)
def records_page(request: Request):
    return dashboard_response(request, "records", "Records", "Research sessions and exports")


@app.get("/participants", response_class=HTMLResponse)
def participants_page(request: Request):
    return templates.TemplateResponse(request=request, name="participants.html",
                                      context={"app_name": settings.app_name,
                                               "identity": getattr(request.state, "identity", None)})


@app.get("/users", response_class=HTMLResponse)
def users_page(request: Request):
    return templates.TemplateResponse(request=request, name="users.html",
                                      context={"app_name": settings.app_name,
                                               "identity": getattr(request.state, "identity", None)})


@app.get("/attention-task", response_class=HTMLResponse)
def attention_task_page(request: Request):
    # Preserve old bookmarks that used ?operator or ?operator=1.
    if "operator" in request.query_params:
        return RedirectResponse("/attention-task/operator", status_code=307)
    return templates.TemplateResponse(request=request, name="attention-task.html", context={"app_name": settings.app_name})


@app.get("/attention-task/operator", response_class=HTMLResponse)
def attention_task_operator_page(request: Request):
    return templates.TemplateResponse(request=request, name="attention-task.html", context={"app_name": settings.app_name})


@app.get("/shape-matching", response_class=HTMLResponse)
def shape_matching_preview(request: Request):
    """Authenticated, local-only game preview; no session records are written."""
    return templates.TemplateResponse(request=request, name="shape-matching.html",
                                      context={"app_name": settings.app_name})


@app.get("/reports/{session_id}", response_class=HTMLResponse)
def report_page(request: Request, session_id: int):
    identity = getattr(request.state, "identity", None)
    session = repository.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if identity and identity.role in {"operator", "reviewer"} and session.operator_id != identity.user_id:
        raise HTTPException(status_code=403, detail="This report is not assigned to your account")
    return templates.TemplateResponse(request=request, name="reports.html",
                                      context={"app_name": settings.app_name, "session_id": session_id})


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    identity = getattr(request.state, "identity", None)
    if settings.auth_enabled and not valid_admin_unlock(request.cookies.get(ADMIN_UNLOCK_COOKIE), identity):
        return RedirectResponse("/system-setup?next=/settings", status_code=303)
    return templates.TemplateResponse(request=request, name="settings.html", context={"app_name": settings.app_name})


@app.get("/calibration", response_class=HTMLResponse)
def calibration_page(request: Request, mode: str = "verification"):
    identity = getattr(request.state, "identity", None)
    if mode == "system" and settings.auth_enabled and not valid_admin_unlock(request.cookies.get(ADMIN_UNLOCK_COOKIE), identity):
        return RedirectResponse("/system-setup?next=/calibration", status_code=303)
    if mode == "system":
        # Keep a single owner-facing calibration workflow. Participant quick
        # verification remains on this route in verification mode.
        return RedirectResponse("/setup?step=4", status_code=303)
    return templates.TemplateResponse(request=request, name="calibration.html", context={"app_name": settings.app_name})


@app.get("/hardware", response_class=HTMLResponse)
def hardware_page(request: Request):
    identity = getattr(request.state, "identity", None)
    if settings.auth_enabled and not valid_admin_unlock(request.cookies.get(ADMIN_UNLOCK_COOKIE), identity):
        return RedirectResponse("/system-setup?next=/hardware", status_code=303)
    return templates.TemplateResponse(request=request, name="hardware.html", context={"app_name": settings.app_name})


@app.get("/setup", response_class=HTMLResponse)
def setup_page(request: Request, step: int | None = None):
    identity = getattr(request.state, "identity", None)
    if identity and identity.role not in {"owner", "admin"}:
        return templates.TemplateResponse(request=request, name="setup-required.html", status_code=403,
            context={"app_name": settings.app_name,
                     "message": "Ask the owner or administrator to complete the one-time system setup."})
    setup = setup_status_payload()
    if (setup["completed"] and settings.auth_enabled and
            not valid_admin_unlock(request.cookies.get(ADMIN_UNLOCK_COOKIE), identity)):
        return RedirectResponse("/system-setup?next=/setup", status_code=303)
    return templates.TemplateResponse(request=request, name="setup.html",
        context={"app_name": settings.app_name, "requested_step": step})


@app.get("/system-setup", response_class=HTMLResponse)
def system_setup_unlock_page(request: Request, next: str = "/system-setup"):
    identity = getattr(request.state, "identity", None)
    safe_next = next if next in {"/system-setup", "/settings", "/calibration", "/hardware", "/setup"} else "/system-setup"
    if not settings.auth_enabled:
        return templates.TemplateResponse(request=request, name="system-setup.html",
            context={"app_name": settings.app_name, "identity": identity})
    if settings.auth_enabled and valid_admin_unlock(request.cookies.get(ADMIN_UNLOCK_COOKIE), identity):
        if safe_next != "/system-setup":
            return RedirectResponse(safe_next, status_code=303)
        return templates.TemplateResponse(request=request, name="system-setup.html",
            context={"app_name": settings.app_name, "identity": identity})
    return templates.TemplateResponse(request=request, name="system-setup-unlock.html",
        context={"app_name": settings.app_name, "error": None, "next_path": safe_next})


@app.post("/system-setup", response_class=HTMLResponse)
def system_setup_unlock(request: Request, access_key: str = Form(...), next: str = Form("/system-setup")):
    current = getattr(request.state, "identity", None)
    supplied = authenticate_access_key(access_key)
    safe_next = next if next in {"/system-setup", "/settings", "/calibration", "/hardware", "/setup"} else "/system-setup"
    if (supplied is None or supplied.role not in {"owner", "admin"} or current is None or
            (current.user_id is not None and current.user_id != supplied.user_id)):
        repository.add_audit_event("system_setup.unlock", current.full_name if current else "unknown",
                                   request.client.host if request.client else None, False)
        return templates.TemplateResponse(request=request, name="system-setup-unlock.html", status_code=401,
            context={"app_name": settings.app_name, "error": "Owner or administrator access key required.",
                     "next_path": safe_next})
    response = RedirectResponse(safe_next, status_code=303)
    response.set_cookie(ADMIN_UNLOCK_COOKIE, issue_admin_unlock(current), max_age=900,
                        httponly=True, samesite="strict", secure=False, path="/")
    repository.add_audit_event("system_setup.unlock", current.full_name,
                               request.client.host if request.client else None)
    return response


@app.get("/preview/{camera_name}")
def camera_preview(camera_name: str, overlays: bool = True) -> StreamingResponse:
    if camera_name not in {"face", "body"}:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Unknown camera")
    if not overlays:
        stream = camera_system.preview_stream(camera_name)
    elif not settings.mock_mode and camera_name == "face":
        stream = analysis_preview_stream("face")
    elif not settings.mock_mode and camera_name == "body":
        stream = analysis_preview_stream("body")
    else:
        stream = camera_system.preview_stream(camera_name)
    return StreamingResponse(
        stream,
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


def analysis_preview_stream(camera_name: str):
    while True:
        service = face_analysis_service if camera_name == "face" else body_analysis_service
        manager = camera_system.face if camera_name == "face" else camera_system.body
        frame = service.annotated_frame()
        if frame is None:
            frame = camera_system._status_frame(camera_name, manager.stats.status)
        ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 78])
        if ok:
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + encoded.tobytes() + b"\r\n"
        time.sleep(1 / min(settings.camera_fps, 15))


@app.websocket("/ws/monitor")
async def monitor_socket(websocket: WebSocket) -> None:
    if settings.auth_enabled and not valid_token(websocket.cookies.get(COOKIE_NAME)):
        await websocket.close(code=4401)
        return
    await websocket.accept()
    try:
        while True:
            if settings.mock_mode:
                payload = mock_monitor.snapshot()
                payload["session_time"] = session_manager.elapsed()
            else:
                face = face_analysis_service.snapshot()
                body = body_analysis_service.snapshot()
                payload = {
                    "data_mode": "REAL CAMERA DATA",
                    "session_time": session_manager.elapsed(),
                    "face_camera_status": camera_system.face.stats.status,
                    "body_camera_status": camera_system.body.stats.status,
                    "face_tracking": face["tracking"],
                    "body_tracking": body["tracking"],
                    "blink_rate": face["blink_rate"],
                    "total_blinks": face["total_blinks"],
                    "yaw": face["yaw"] or 0.0, "pitch": face["pitch"] or 0.0, "roll": face["roll"] or 0.0,
                    "head_movements": face["head_movements"],
                    "body_movement": body["movement_magnitude"], "movement_events": body["movement_events"],
                    "posture_changes": body["posture_changes"],
                    "task_correct": 0, "task_incorrect": 0, "task_missed": 0,
                    "task_accuracy": 0.0, "reaction_time_ms": 0,
                }
            active_session_id = session_manager.active_session_id
            if active_session_id is not None:
                task = attention_task_service.summary(active_session_id)
                payload.update({
                    "task_correct": task["correct"], "task_incorrect": task["incorrect"],
                    "task_missed": task["missed"], "task_accuracy": task["accuracy"],
                    "reaction_time_ms": task["average_reaction_time_ms"] or 0,
                })
            await websocket.send_json(payload)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        logger.info("Monitoring WebSocket disconnected")
