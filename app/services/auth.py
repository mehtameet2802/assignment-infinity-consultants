import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from flask import current_app, g
from sqlalchemy import select
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash

from app.http import (
    auth_not_configured_response,
    invalid_admin_password_response,
    unauthorized_response,
)
from app.models import ApiKey

KEY_PREFIX_DISPLAY_LEN = 10
RAW_KEY_PREFIX = "st_"
ROTATION_GRACE_MINUTES = 5


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _auth_enabled() -> bool:
    return bool(current_app.config.get("AUTH_ENABLED", False))


def _pepper() -> str | None:
    value = current_app.config.get("API_KEY_PEPPER")
    return value if value else None


def _admin_password_hash() -> str | None:
    value = current_app.config.get("ADMIN_PASSWORD_HASH")
    return value if value else None


def auth_is_configured() -> bool:
    if not _auth_enabled():
        return True
    return bool(_pepper() and _admin_password_hash())


def generate_raw_api_key() -> str:
    return f"{RAW_KEY_PREFIX}{secrets.token_urlsafe(32)}"


def hash_api_key(raw_key: str, pepper: str) -> str:
    return hmac.new(
        pepper.encode("utf-8"),
        raw_key.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def key_prefix_for_display(raw_key: str) -> str:
    return raw_key[:KEY_PREFIX_DISPLAY_LEN]


def format_prefix_label(prefix: str) -> str:
    return f"{prefix}…"


def is_api_key_record_valid(record: ApiKey, now: datetime | None = None) -> bool:
    moment = now or utc_now()
    if record.revoked_at is not None:
        return False
    if record.expires_at is not None and record.expires_at <= moment:
        return False
    return True


def has_usable_api_key(db: Session, now: datetime | None = None) -> bool:
    moment = now or utc_now()
    records = db.scalars(select(ApiKey)).all()
    return any(is_api_key_record_valid(record, moment) for record in records)


def create_api_key_record(db: Session, raw_key: str, pepper: str) -> ApiKey:
    record = ApiKey(
        key_hash=hash_api_key(raw_key, pepper),
        key_prefix=key_prefix_for_display(raw_key),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def lookup_api_key(db: Session, raw_key: str, pepper: str) -> ApiKey | None:
    digest = hash_api_key(raw_key, pepper)
    return db.scalar(select(ApiKey).where(ApiKey.key_hash == digest))


def authenticate_raw_key(db: Session, raw_key: str | None) -> ApiKey | None:
    if not raw_key:
        return None
    pepper = _pepper()
    if not pepper:
        return None
    record = lookup_api_key(db, raw_key, pepper)
    if record is None or not is_api_key_record_valid(record):
        return None
    record.last_used_at = utc_now()
    db.commit()
    return record


def verify_admin_password(password: str) -> bool:
    stored = _admin_password_hash()
    if not stored:
        return False
    return check_password_hash(stored, password)


def api_key_metadata(record: ApiKey) -> dict[str, Any]:
    return {
        "prefix": format_prefix_label(record.key_prefix),
        "created_at": record.created_at.isoformat(),
        "last_used_at": record.last_used_at.isoformat() if record.last_used_at else None,
        "expires_at": record.expires_at.isoformat() if record.expires_at else None,
    }


def require_api_key():
    """Return None on success; sets g.api_key. Otherwise return (response, status)."""
    if not _auth_enabled():
        return None
    if not auth_is_configured():
        return auth_not_configured_response()
    from app.database import get_db

    raw_key = _extract_request_api_key()
    record = authenticate_raw_key(get_db(), raw_key)
    if record is None:
        return unauthorized_response()
    g.api_key = record
    return None


def _extract_request_api_key() -> str | None:
    from flask import request

    value = request.headers.get("X-API-Key")
    if value is None or value == "":
        return None
    return value.strip()


def rotate_api_key(db: Session, current_record: ApiKey, password: str) -> tuple[str, ApiKey, datetime]:
    if not verify_admin_password(password):
        raise PermissionError("invalid_admin_password")
    pepper = _pepper()
    if not pepper:
        raise RuntimeError("auth_not_configured")
    raw_new = generate_raw_api_key()
    new_record = create_api_key_record(db, raw_new, pepper)
    grace_until = utc_now() + timedelta(minutes=ROTATION_GRACE_MINUTES)
    current_record.expires_at = grace_until
    db.commit()
    db.refresh(current_record)
    return raw_new, new_record, grace_until
