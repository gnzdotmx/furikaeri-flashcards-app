"""Tests for auth endpoints (register, login, me)."""

import logging
import os
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(autouse=True)
def _bypass_rate_limit_in_tests():
    old = os.environ.get("TESTING")
    os.environ["TESTING"] = "1"
    try:
        yield
    finally:
        if old is None:
            os.environ.pop("TESTING", None)
        else:
            os.environ["TESTING"] = old


# JWT secret for tests (required by settings; at least 32 chars for HS256).
TEST_JWT_SECRET = "test-jwt-secret-at-least-32-bytes-for-hs256"


def _test_client():
    tmp = Path(tempfile.mkdtemp(prefix="furikaeri_auth_"))
    db_path = str(tmp / "test.sqlite")
    os.environ["SQLITE_PATH"] = db_path
    os.environ["DATA_DIR"] = str(tmp)
    os.environ["AUDIO_CACHE_DIR"] = str(tmp / "audio_cache")
    os.environ["JWT_SECRET"] = TEST_JWT_SECRET
    app = create_app()
    return TestClient(app)


def test_auth_register_success():
    client = _test_client()
    r = client.post(
        "/api/auth/register",
        json={"username": "alice", "email": "alice@example.com", "password": "securepass123"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data.get("token_type") == "bearer"
    assert data.get("user", {}).get("username") == "alice"
    assert data.get("user", {}).get("email") == "alice@example.com"
    assert "id" in data["user"]


def test_auth_no_passwords_or_tokens_in_logs(caplog):
    """Logging policy: no passwords or tokens must appear in any log during auth (register/login)."""
    caplog.set_level(logging.DEBUG, logger="app")
    # Also capture root so any app log that bubbles up is seen
    caplog.set_level(logging.DEBUG)
    client = _test_client()
    password = "s3cr3t_n0_log_m3"
    r = client.post(
        "/api/auth/register",
        json={"username": "nologuser", "email": "nolog@example.com", "password": password},
    )
    assert r.status_code == 200
    data = r.json()
    token = data.get("access_token") or ""
    assert token, "test needs a token to assert it is not logged"
    r2 = client.post("/api/auth/login", json={"username": "nologuser", "password": password})
    assert r2.status_code == 200
    for record in caplog.records:
        msg = (record.getMessage() or "") + " " + str(getattr(record, "args", ()))
        if record.exc_info and record.exc_info[1]:
            msg += " " + str(record.exc_info[1])
            if record.exc_info[2]:
                msg += " " + str(record.exc_text or "")
        assert password not in msg, "password must not appear in logs"
        assert token not in msg, "access_token must not appear in logs"


def test_auth_register_duplicate_username():
    client = _test_client()
    payload = {"username": "bob", "email": "bob1@example.com", "password": "pass123456"}
    r1 = client.post("/api/auth/register", json=payload)
    assert r1.status_code == 200
    r2 = client.post("/api/auth/register", json={**payload, "email": "bob2@example.com"})
    assert r2.status_code == 409
    assert "already taken" in (r2.json().get("detail") or "").lower()


def test_auth_register_duplicate_email():
    client = _test_client()
    payload = {"username": "u1", "email": "same@example.com", "password": "pass123456"}
    client.post("/api/auth/register", json=payload)
    r2 = client.post("/api/auth/register", json={**payload, "username": "u2"})
    assert r2.status_code == 409
    assert "email" in (r2.json().get("detail") or "").lower()


def test_auth_register_validation_short_password():
    client = _test_client()
    r = client.post(
        "/api/auth/register",
        json={"username": "u", "email": "u@x.com", "password": "short"},
    )
    assert r.status_code == 422


def test_auth_register_invalid_email_format():
    """Registration rejects obviously invalid email formats with 400."""
    client = _test_client()
    invalid_emails = [
        "no-at-sign.com",
        "missing-tld@domain",
        "double@@example.com",
        "@nodomain.com",
        "nolocal@.com",
        "spaces in@local.com",
        "",
    ]
    for i, email in enumerate(invalid_emails):
        # Use unique username so duplicate-username doesn't cause 409
        username = f"u{i}"
        r = client.post(
            "/api/auth/register",
            json={"username": username, "email": email, "password": "validpass123"},
        )
        assert r.status_code == 400, f"Expected 400 for {email!r}"
        assert "invalid" in (r.json().get("detail") or "").lower()


def test_auth_register_valid_email_formats():
    """Registration accepts common valid email formats."""
    client = _test_client()
    valid_cases = [
        ("user+tag@example.com", "userplus"),
        ("user.name@example.co.uk", "userdot"),
        ("a@b.co", "short"),
    ]
    for email, username in valid_cases:
        r = client.post(
            "/api/auth/register",
            json={"username": username, "email": email, "password": "validpass123"},
        )
        assert r.status_code == 200, f"Expected 200 for {email!r}: {r.json()}"
        assert r.json().get("user", {}).get("email") == email


def test_auth_login_success():
    client = _test_client()
    client.post(
        "/api/auth/register",
        json={"username": "logintest", "email": "login@example.com", "password": "mypass123"},
    )
    r = client.post("/api/auth/login", json={"username": "logintest", "password": "mypass123"})
    assert r.status_code == 200
    assert "access_token" in r.json()
    assert r.json().get("user", {}).get("username") == "logintest"


def test_auth_login_wrong_password():
    client = _test_client()
    client.post(
        "/api/auth/register",
        json={"username": "u", "email": "u@x.com", "password": "correct123"},
    )
    r = client.post("/api/auth/login", json={"username": "u", "password": "wrongpass"})
    assert r.status_code == 401


def test_auth_me_without_token_returns_401():
    """Protected routes require valid session; no single-user fallback."""
    client = _test_client()
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_auth_me_with_token_returns_user():
    client = _test_client()
    reg = client.post(
        "/api/auth/register",
        json={"username": "meuser", "email": "me@x.com", "password": "pass123456"},
    )
    assert reg.status_code == 200
    token = reg.json()["access_token"]
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json().get("username") == "meuser"


def test_protected_endpoint_with_token():
    client = _test_client()
    reg = client.post(
        "/api/auth/register",
        json={"username": "prot", "email": "prot@x.com", "password": "pass123456"},
    )
    assert reg.status_code == 200
    token = reg.json()["access_token"]
    r = client.get("/api/users/settings", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_protected_endpoint_with_cookie():
    """Middleware accepts session token from cookie (no Authorization header)."""
    client = _test_client()
    r = client.post(
        "/api/auth/register",
        json={"username": "cookieuser", "email": "cookie@x.com", "password": "pass123456"},
    )
    assert r.status_code == 200
    # Cookie set by register response; next request sends it automatically
    r_me = client.get("/api/auth/me")
    assert r_me.status_code == 200
    assert r_me.json().get("username") == "cookieuser"


def test_auth_logout_invalidates_session():
    client = _test_client()
    reg = client.post(
        "/api/auth/register",
        json={"username": "logoutuser", "email": "logout@x.com", "password": "pass123456"},
    )
    assert reg.status_code == 200
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r_me = client.get("/api/auth/me", headers=headers)
    assert r_me.status_code == 200
    r_logout = client.post("/api/auth/logout", headers=headers)
    assert r_logout.status_code == 200
    r_me_after = client.get("/api/auth/me", headers=headers)
    assert r_me_after.status_code == 401


def test_auth_session_cookie_secure_in_production():
    """When APP_ENV=production, Set-Cookie must include Secure so cookie is only sent over HTTPS."""
    old_env = os.environ.get("APP_ENV")
    try:
        os.environ["APP_ENV"] = "production"
        client = _test_client()
        r = client.post(
            "/api/auth/register",
            json={"username": "secureuser", "email": "secure@example.com", "password": "pass123456"},
        )
        assert r.status_code == 200
        set_cookie = r.headers.get("set-cookie") or ""
        assert "Secure" in set_cookie, "Session cookie must have Secure flag in production"
        assert "HttpOnly" in set_cookie
        assert "samesite=lax" in set_cookie.lower()
    finally:
        if old_env is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = old_env
