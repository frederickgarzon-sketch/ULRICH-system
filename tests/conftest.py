"""Keep automated tests isolated from physical cameras and real records."""

import os
import tempfile
import uuid
from pathlib import Path

os.environ["APP_MODE"] = "mock"
os.environ["SAVE_RAW_VIDEO"] = "false"
os.environ["AUTH_ENABLED"] = "false"
# Tests must be self-contained and must never depend on a developer/client .env.
os.environ["RESEARCHER_ACCESS_KEY"] = "isolated-test-access-key"
os.environ["SESSION_SECRET"] = "isolated-test-session-secret-with-at-least-32-characters"
test_database = Path(tempfile.gettempdir()) / f"behavioral-monitoring-test-{uuid.uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{test_database.as_posix()}"
