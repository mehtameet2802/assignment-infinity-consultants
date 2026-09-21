from datetime import timedelta

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash

from app import create_app
from app.models import ApiKey
from app.services.auth import (
    create_api_key_record,
    generate_raw_api_key,
    hash_api_key,
    is_api_key_record_valid,
    utc_now,
)

ADMIN_PASSWORD = "admin-secret"
PEPPER = "test-pepper-value-32chars-min"


@pytest.fixture
def auth_app(db_session: Session) -> Flask:
    return create_app(
        {
            "DB_SESSION": db_session,
            "AUTH_ENABLED": True,
            "API_KEY_PEPPER": PEPPER,
            "ADMIN_PASSWORD_HASH": generate_password_hash(ADMIN_PASSWORD),
        }
    )


@pytest.fixture
def auth_client(auth_app: Flask) -> FlaskClient:
    return auth_app.test_client()


@pytest.fixture
def raw_api_key(db_session: Session) -> str:
    raw = generate_raw_api_key()
    create_api_key_record(db_session, raw, PEPPER)
    return raw


def _headers(key: str | None = None) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if key is not None:
        headers["X-API-Key"] = key
    return headers


def test_api_key_hashing_is_deterministic():
    raw = generate_raw_api_key()
    assert hash_api_key(raw, PEPPER) == hash_api_key(raw, PEPPER)


def test_raw_key_is_not_stored(db_session: Session, raw_api_key: str):
    from sqlalchemy import select

    record = db_session.scalar(select(ApiKey))
    assert record.key_hash != raw_api_key
    assert raw_api_key not in record.key_hash


def test_missing_key_returns_401(auth_client: FlaskClient):
    response = auth_client.get("/dashboard", query_string={"month": "2026-09"})
    assert response.status_code == 401
    assert response.get_json()["error"] == "unauthorized"


def test_invalid_key_returns_401(auth_client: FlaskClient):
    response = auth_client.get(
        "/dashboard",
        query_string={"month": "2026-09"},
        headers=_headers("st_invalid-key"),
    )
    assert response.status_code == 401


def test_valid_key_allows_dashboard(auth_client: FlaskClient, raw_api_key: str):
    response = auth_client.get(
        "/dashboard",
        query_string={"month": "2026-09"},
        headers=_headers(raw_api_key),
    )
    assert response.status_code == 200


def test_revoked_key_fails(db_session: Session, auth_client: FlaskClient, raw_api_key: str):
    from sqlalchemy import select

    record = db_session.scalar(select(ApiKey))
    record.revoked_at = utc_now()
    db_session.commit()
    response = auth_client.get(
        "/dashboard",
        query_string={"month": "2026-09"},
        headers=_headers(raw_api_key),
    )
    assert response.status_code == 401


def test_expired_key_fails(db_session: Session, auth_client: FlaskClient, raw_api_key: str):
    from sqlalchemy import select

    record = db_session.scalar(select(ApiKey))
    record.expires_at = utc_now() - timedelta(minutes=1)
    db_session.commit()
    assert is_api_key_record_valid(record) is False
    response = auth_client.get(
        "/dashboard",
        query_string={"month": "2026-09"},
        headers=_headers(raw_api_key),
    )
    assert response.status_code == 401


def test_health_and_static_remain_public(auth_client: FlaskClient):
    assert auth_client.get("/health").status_code == 200
    assert auth_client.get("/").status_code == 200
    assert auth_client.get("/analytics").status_code == 200
    assert auth_client.get("/settings/security").status_code == 200
    assert auth_client.get("/static/js/app.js").status_code == 200


def test_expenses_json_protected_html_public(auth_client: FlaskClient, raw_api_key: str):
    assert auth_client.get("/expenses").status_code == 401
    html = auth_client.get("/expenses", headers={"Accept": "text/html"})
    assert html.status_code == 200
    assert b"Spend Tracker" in html.data
    assert (
        auth_client.get("/expenses", headers=_headers(raw_api_key)).status_code == 200
    )


def test_auth_verify_returns_metadata_only(auth_client: FlaskClient, raw_api_key: str):
    response = auth_client.get("/auth/verify", headers=_headers(raw_api_key))
    body = response.get_json()
    assert body["authenticated"] is True
    assert "prefix" in body["key"]
    assert "key_hash" not in body


def test_rotation_requires_valid_key(auth_client: FlaskClient):
    response = auth_client.post(
        "/auth/api-key/rotate",
        json={"password": ADMIN_PASSWORD},
    )
    assert response.status_code == 401


def test_rotation_rejects_bad_password(auth_client: FlaskClient, raw_api_key: str):
    response = auth_client.post(
        "/auth/api-key/rotate",
        json={"password": "wrong"},
        headers=_headers(raw_api_key),
    )
    assert response.status_code == 403
    assert response.get_json()["error"] == "invalid_admin_password"


def test_rotation_returns_new_raw_key_once(auth_client: FlaskClient, raw_api_key: str):
    response = auth_client.post(
        "/auth/api-key/rotate",
        json={"password": ADMIN_PASSWORD},
        headers=_headers(raw_api_key),
    )
    assert response.status_code == 200
    body = response.get_json()
    assert "api_key" in body
    assert body["api_key"].startswith("st_")
    assert "key_hash" not in body


def test_rotation_grace_window_and_expiry(
    db_session: Session, auth_client: FlaskClient, raw_api_key: str
):
    rotate = auth_client.post(
        "/auth/api-key/rotate",
        json={"password": ADMIN_PASSWORD},
        headers=_headers(raw_api_key),
    )
    new_key = rotate.get_json()["api_key"]
    assert (
        auth_client.get(
            "/dashboard",
            query_string={"month": "2026-09"},
            headers=_headers(raw_api_key),
        ).status_code
        == 200
    )
    assert (
        auth_client.get(
            "/dashboard",
            query_string={"month": "2026-09"},
            headers=_headers(new_key),
        ).status_code
        == 200
    )
    records = db_session.scalars(
        __import__("sqlalchemy").select(ApiKey).order_by(ApiKey.id)
    ).all()
    old = records[0]
    old.expires_at = utc_now() - timedelta(minutes=1)
    db_session.commit()
    assert (
        auth_client.get(
            "/dashboard",
            query_string={"month": "2026-09"},
            headers=_headers(raw_api_key),
        ).status_code
        == 401
    )
    assert (
        auth_client.get(
            "/dashboard",
            query_string={"month": "2026-09"},
            headers=_headers(new_key),
        ).status_code
        == 200
    )


def test_auth_not_configured_returns_503(db_session: Session):
    app = create_app(
        {
            "DB_SESSION": db_session,
            "AUTH_ENABLED": True,
            "API_KEY_PEPPER": None,
            "ADMIN_PASSWORD_HASH": None,
        }
    )
    client = app.test_client()
    response = client.get("/dashboard", query_string={"month": "2026-09"})
    assert response.status_code == 503
    assert response.get_json()["error"] == "auth_not_configured"


def test_auth_disabled_preserves_open_api(client: FlaskClient):
    response = client.get("/expenses")
    assert response.status_code == 200


def test_auth_routes_return_404_when_auth_disabled(client: FlaskClient):
    assert client.get("/auth/verify").status_code == 404
    assert client.get("/auth/api-key").status_code == 404
    assert client.post("/auth/api-key/rotate", json={"password": "x"}).status_code == 404
    body = client.get("/auth/verify").get_json()
    assert body["error"] == "auth_disabled"
