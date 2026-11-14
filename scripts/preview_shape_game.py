"""Loopback-only Shape Matching preview; no app imports, records or cameras."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
ASSETS = {
    "/static/css/attention-task.css": ("static/css/attention-task.css", "text/css"),
    "/static/css/shape-matching.css": ("static/css/shape-matching.css", "text/css"),
    "/static/js/shape-matching.js": ("static/js/shape-matching.js", "text/javascript"),
    "/static/js/shape-matching-core.js": ("static/js/shape-matching-core.js", "text/javascript"),
}


class Preview(BaseHTTPRequestHandler):
    def send(self, status, data, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path in {"/", "/shape-matching"}:
            html = (ROOT / "templates/shape-matching.html").read_text(encoding="utf-8")
            html = html.replace("{{ app_name }}", "Local game preview")
            html = html.replace('id="pair"', 'id="pair" hidden')
            html = html.replace('id="operator-stop-shape"', 'id="operator-stop-shape" hidden')
            # The controller toggles this operator-only button; remove its input
            # action from the served script too, without modifying the real app.
            html = html.replace('id="recording-note">', 'id="recording-note">PREVIEW SERVER: no records, pairing or cameras. ')
            self.send(200, html.encode(), "text/html")
        elif path in ASSETS:
            relative, mime = ASSETS[path]
            data = (ROOT / relative).read_text(encoding="utf-8")
            if relative.endswith("shape-matching.js"):
                data = data.replace("$('operator-stop-shape').hidden=!!token;", "$('operator-stop-shape').hidden=true;")
            self.send(200, data.encode(), mime)
        else:
            self.send(404, b"Preview only. Open /shape-matching", "text/plain")

    def do_POST(self):
        self.send(409, json.dumps({"detail": "Preview only: recording/pairing is disabled."}).encode(), "application/json")

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    print("Shape Matching PREVIEW only: http://127.0.0.1:8765/shape-matching", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8765), Preview).serve_forever()
