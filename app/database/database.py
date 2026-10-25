"""SQLAlchemy engine and session lifecycle."""

from datetime import datetime, timezone

from sqlalchemy import create_engine, event, inspect, text, update
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def configure_sqlite(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


def initialize_database() -> None:
    from app.database import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_columns()


def _migrate_sqlite_columns() -> None:
    """Small additive migration for installations created before account support."""
    if not settings.database_url.startswith("sqlite"):
        return
    additions = {
        "participants": {
            "date_of_birth": "VARCHAR(10)", "sex": "VARCHAR(30)", "gender": "VARCHAR(50)",
            "grade_level": "VARCHAR(50)", "school_site": "VARCHAR(120)", "address": "VARCHAR(240)",
            "guardian_name": "VARCHAR(120)", "consent_reference": "VARCHAR(120)",
            "consent_date": "VARCHAR(10)", "diagnosis_status": "VARCHAR(40)",
            "medication_notes": "TEXT", "accommodations": "TEXT", "research_notes": "TEXT",
            "created_by_user_id": "INTEGER",
        },
        "sessions": {"operator_id": "INTEGER"},
        "user_accounts": {"access_pin": "TEXT"},
        "calibration_profiles": {"profile_type": "VARCHAR(20) DEFAULT 'participant'", "created_by_user_id": "INTEGER"},
        "attention_trials": {"task_run_id": "INTEGER"},
        "blink_events": {"closure_duration_seconds": "FLOAT", "phase": "VARCHAR(20) DEFAULT 'baseline'"},
        "head_pose_samples": {"valid": "BOOLEAN DEFAULT 1", "status": "VARCHAR(40)",
                              "phase": "VARCHAR(20) DEFAULT 'baseline'"},
        "head_movement_events": {"phase": "VARCHAR(20) DEFAULT 'baseline'"},
        "body_movement_samples": {"valid": "BOOLEAN DEFAULT 1", "status": "VARCHAR(40)",
                                  "phase": "VARCHAR(20) DEFAULT 'baseline'"},
        "body_movement_events": {"phase": "VARCHAR(20) DEFAULT 'baseline'"},
        "posture_events": {"phase": "VARCHAR(20) DEFAULT 'baseline'"},
    }
    inspector = inspect(engine)
    with engine.begin() as connection:
        for table, columns in additions.items():
            existing = {item["name"] for item in inspector.get_columns(table)}
            for name, sql_type in columns.items():
                if name not in existing:
                    connection.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {sql_type}'))
        if "user_accounts" in inspector.get_table_names():
            connection.execute(text("UPDATE user_accounts SET role='operator' WHERE role='reviewer'"))
            from app.services.access_control import encrypt_recoverable_pin
            legacy_pins = connection.execute(text(
                "SELECT id, access_pin FROM user_accounts WHERE access_pin IS NOT NULL AND access_pin NOT LIKE 'enc:v1:%'"
            )).fetchall()
            for user_id, pin in legacy_pins:
                if isinstance(pin, str) and pin.isdigit() and len(pin) == 6:
                    connection.execute(text("UPDATE user_accounts SET access_pin=:pin WHERE id=:id"),
                                       {"pin": encrypt_recoverable_pin(pin), "id": user_id})


def recover_interrupted_sessions() -> int:
    """Mark sessions left active by a previous crash as interrupted."""
    from app.database.models import MonitoringSession

    with SessionLocal() as db:
        result = db.execute(
            update(MonitoringSession)
            .where(MonitoringSession.status == "active")
            .values(status="interrupted", end_time=datetime.now(timezone.utc))
        )
        db.commit()
        return int(result.rowcount or 0)
