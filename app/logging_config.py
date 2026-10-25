"""Console and size-bounded local file logging."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from app.config import ROOT_DIR, settings


def configure_logging() -> None:
    log_dir = ROOT_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.log_level, logging.INFO))
    if not any(isinstance(handler, RotatingFileHandler) for handler in root.handlers):
        file_handler = RotatingFileHandler(
            log_dir / "application.log", maxBytes=settings.log_max_bytes,
            backupCount=settings.log_backup_count, encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    if not any(type(handler) is logging.StreamHandler for handler in root.handlers):
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        root.addHandler(console)

