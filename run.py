"""Run the local Behavioral Monitoring System server."""

from __future__ import annotations

import socket
import os
import threading
import time
import webbrowser

import uvicorn
import torch

from app.config import settings


def lan_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "LAN-IP"
    finally:
        sock.close()


def port_in_use(host: str, port: int) -> bool:
    """Return True when another local server is already listening."""
    target = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.35)
        return sock.connect_ex((target, port)) == 0


def print_access_details() -> None:
    if settings.auth_enabled:
        print("Research login: ENABLED")
        print(f"Access key:     {settings.researcher_access_key}")
        print("Security:       Keep this local key private")
    else:
        print("Research login: DISABLED")


def open_browser_when_ready() -> None:
    """Open the local login only after this process is listening."""
    for _ in range(60):
        time.sleep(0.5)
        if port_in_use("127.0.0.1", settings.server_port):
            webbrowser.open(f"http://127.0.0.1:{settings.server_port}/login")
            return


if __name__ == "__main__":
    print("=" * 48)
    print(settings.app_name)
    print("=" * 48)
    print(f"Server:        http://127.0.0.1:{settings.server_port}")
    print(f"LAN dashboard: http://{lan_ip()}:{settings.server_port}")
    print(f"Mode:          {settings.app_mode.upper()}")
    print(f"Face camera:   {settings.face_camera_source}")
    print(f"Body camera:   {settings.body_camera_source}")
    print(f"Database:      {settings.database_url}")
    print(f"AI device:     {'CUDA' if torch.cuda.is_available() else 'CPU'}")
    print("Raw recording: OFF" if not settings.save_raw_video else "Raw recording: ON")
    print_access_details()
    print("=" * 48)
    if port_in_use(settings.server_host, settings.server_port):
        print("")
        print(f"PORT {settings.server_port} IS ALREADY IN USE.")
        print("This CLEAN copy did not start; the browser may be showing an older copy.")
        print("Close the existing server window with Ctrl+C, then run this copy again.")
        raise SystemExit(2)
    if os.environ.get("OPEN_LOCAL_BROWSER") == "1":
        threading.Thread(target=open_browser_when_ready, daemon=True).start()
    # Participant pairing capabilities travel in short-lived query parameters.
    # Uvicorn access logs include the raw URL, so keep them off in the normal
    # launcher to avoid retaining those tokens in console or redirected logs.
    # Application lifecycle, audit, warning, and error logs remain enabled.
    uvicorn.run("app.main:app", host=settings.server_host, port=settings.server_port,
                reload=False, access_log=False)
