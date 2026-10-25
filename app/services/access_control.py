"""Small signed-cookie access layer for the local research prototype."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from app.config import settings
from cryptography.fernet import Fernet, InvalidToken

COOKIE_NAME = "researcher_session"
ADMIN_UNLOCK_COOKIE = "system_setup_unlock"


@dataclass(frozen=True)
class Identity:
    user_id: int | None
    full_name: str
    role: str
    legacy_owner: bool = False


def configuration_valid() -> bool:
    return bool(settings.researcher_access_key and len(settings.session_secret) >= 32)


def token_hash(candidate: str) -> str:
    return hmac.new(settings.session_secret.encode("utf-8"), candidate.encode("utf-8"), hashlib.sha256).hexdigest()


def generate_access_token() -> str:
    """Return a tablet-friendly six-digit local access PIN."""
    return f"{secrets.randbelow(1_000_000):06d}"


def encrypt_recoverable_pin(pin: str) -> str:
    """Encrypt an administrator-recoverable PIN with the installation secret."""
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.session_secret.encode("utf-8")).digest())
    return "enc:v1:" + Fernet(key).encrypt(pin.encode("ascii")).decode("ascii")


def decrypt_recoverable_pin(value: str | None) -> str | None:
    if not value:
        return None
    if not value.startswith("enc:v1:"):
        return value if value.isdigit() and len(value) == 6 else None
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.session_secret.encode("utf-8")).digest())
    try:
        return Fernet(key).decrypt(value[7:].encode("ascii")).decode("ascii")
    except (InvalidToken, ValueError):
        return None


def authenticate_access_key(candidate: str) -> Identity | None:
    if configuration_valid() and hmac.compare_digest(candidate, settings.researcher_access_key):
        return Identity(None, "System Owner", "owner", True)
    if not configuration_valid():
        return None
    from app.database.repository import repository
    item = repository.find_user_by_token_hash(token_hash(candidate))
    if item is None or not item.active:
        return None
    expiry = item.expires_at
    if expiry is not None:
        if expiry.tzinfo is None: expiry = expiry.replace(tzinfo=timezone.utc)
        if expiry <= datetime.now(timezone.utc): return None
    repository.record_user_login(item.id)
    return Identity(item.id, item.full_name, item.role)


def valid_access_key(candidate: str) -> bool:
    return authenticate_access_key(candidate) is not None


def issue_token(identity: Identity | None = None) -> str:
    identity = identity or Identity(None, "System Owner", "owner", True)
    payload = {"uid": identity.user_id, "name": identity.full_name, "role": identity.role,
               "exp": int(time.time()) + settings.auth_session_hours * 3600}
    encoded = _encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(settings.session_secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).digest()
    return f"{encoded}.{_encode(signature)}"


def token_identity(token: str | None) -> Identity | None:
    if not token or not configuration_valid():
        return None
    try:
        encoded, supplied = token.split(".", 1)
        expected = hmac.new(settings.session_secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(_decode(supplied), expected):
            return None
        payload = json.loads(_decode(encoded))
        if payload.get("role") not in {"owner", "admin", "operator", "reviewer"} or int(payload.get("exp", 0)) <= int(time.time()):
            return None
        user_id = payload.get("uid")
        if user_id is not None:
            from app.database.repository import repository
            account = repository.get_user_account(int(user_id))
            if account is None or not account.active: return None
        return Identity(int(user_id) if user_id is not None else None,
                        str(payload.get("name") or "User"), str(payload["role"]), user_id is None)
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def valid_token(token: str | None) -> bool:
    return token_identity(token) is not None


def issue_admin_unlock(identity: Identity, lifetime_seconds: int = 900) -> str:
    payload = {"uid": identity.user_id, "role": identity.role,
               "exp": int(time.time()) + lifetime_seconds, "purpose": "system-setup"}
    encoded = _encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(settings.session_secret.encode("utf-8"),
                         ("admin:" + encoded).encode("ascii"), hashlib.sha256).digest()
    return f"{encoded}.{_encode(signature)}"


def valid_admin_unlock(value: str | None, identity: Identity | None) -> bool:
    if not value or identity is None or identity.role not in {"owner", "admin"}:
        return False
    try:
        encoded, supplied = value.split(".", 1)
        expected = hmac.new(settings.session_secret.encode("utf-8"),
                            ("admin:" + encoded).encode("ascii"), hashlib.sha256).digest()
        payload = json.loads(_decode(encoded))
        return (hmac.compare_digest(_decode(supplied), expected) and
                payload.get("purpose") == "system-setup" and
                payload.get("uid") == identity.user_id and payload.get("role") == identity.role and
                int(payload.get("exp", 0)) > int(time.time()))
    except (ValueError, TypeError, json.JSONDecodeError):
        return False


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
