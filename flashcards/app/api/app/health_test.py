import os
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from app.main import create_app


def _health_client(sqlite_path: str, app_env: str = "development"):
    """Create app and client with given SQLITE_PATH and APP_ENV."""
    tmp_base = Path(sqlite_path).parent
    os.environ["SQLITE_PATH"] = sqlite_path
    os.environ["DATA_DIR"] = str(tmp_base)
    os.environ["AUDIO_CACHE_DIR"] = str(tmp_base / "audio_cache")
    os.environ["JWT_SECRET"] = "test-jwt-secret-at-least-32-bytes-for-hs256"
    os.environ["APP_ENV"] = app_env
    app = create_app()
    return TestClient(app)


def test_health_ok():
    # Use temp paths for tests (avoid /data dependency on read-only systems).
    tmp_base = Path(os.getenv("PYTEST_TMPDIR", "/tmp")) / "furikaeri_health_test"
    tmp_base.mkdir(parents=True, exist_ok=True)
    db_path = str(tmp_base / "furikaeri_test.sqlite")
    client = _health_client(db_path)
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["db"]["ok"] is True


def test_health_exposes_db_path_in_development():
    """In non-production, health response includes actual db path (for debugging)."""
    old_env = os.environ.get("APP_ENV")
    try:
        tmp_base = Path(os.getenv("PYTEST_TMPDIR", "/tmp")) / "furikaeri_health_path_dev"
        tmp_base.mkdir(parents=True, exist_ok=True)
        db_path = str(tmp_base / "dev.sqlite")
        client = _health_client(db_path, app_env="development")
        res = client.get("/health")
        assert res.status_code == 200
        body = res.json()
        assert body["db"]["ok"] is True
        expected_path = str(Path(db_path).resolve())
        assert body["db"]["path"] == expected_path
    finally:
        if old_env is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = old_env


def test_health_redacts_db_path_in_production():
    """In production, health response must not expose full DB path (security)."""
    old_env = os.environ.get("APP_ENV")
    try:
        tmp_base = Path(os.getenv("PYTEST_TMPDIR", "/tmp")) / "furikaeri_health_path_prod"
        tmp_base.mkdir(parents=True, exist_ok=True)
        db_path = str(tmp_base / "prod.sqlite")
        client = _health_client(db_path, app_env="production")
        res = client.get("/health")
        assert res.status_code == 200
        body = res.json()
        assert body["db"]["ok"] is True
        assert body["db"]["path"] == "<redacted>"
        # Ensure no absolute path leaks elsewhere in db payload
        payload_str = str(body["db"])
        assert db_path not in payload_str
    finally:
        if old_env is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = old_env
