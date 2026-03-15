"""Tests for app startup and middleware config (CORS, etc.)."""

import os
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from app.main import create_app


def _env_client(env_overrides):
    tmp = Path(tempfile.mkdtemp(prefix="furikaeri_main_test_"))
    os.environ["SQLITE_PATH"] = str(tmp / "test.sqlite")
    os.environ["DATA_DIR"] = str(tmp)
    os.environ["AUDIO_CACHE_DIR"] = str(tmp / "audio_cache")
    os.environ["JWT_SECRET"] = "test-jwt-secret-at-least-32-bytes-for-hs256"
    for k, v in env_overrides.items():
        os.environ[k] = v
    try:
        app = create_app()
        return TestClient(app)
    finally:
        for k in env_overrides:
            os.environ.pop(k, None)


def test_cors_not_allowed_when_production_and_origins_include_wildcard():
    """In production, CORS must not be enabled when CORS_ALLOW_ORIGINS contains *."""
    client = _env_client({"APP_ENV": "production", "CORS_ALLOW_ORIGINS": "*"})
    # OPTIONS preflight with Origin; if CORS were added with *, we'd see Access-Control-Allow-Origin
    res = client.options("/api/health", headers={"Origin": "https://example.com"})
    allow_origin = res.headers.get("access-control-allow-origin")
    assert allow_origin is None, "Production with * must not add CORS"


def test_cors_allowed_in_production_with_explicit_origins():
    """In production, CORS is enabled when CORS_ALLOW_ORIGINS lists explicit origins (no *)."""
    client = _env_client({
        "APP_ENV": "production",
        "CORS_ALLOW_ORIGINS": "https://app.example.com",
    })
    res = client.options("/api/health", headers={"Origin": "https://app.example.com"})
    allow_origin = res.headers.get("access-control-allow-origin")
    assert allow_origin == "https://app.example.com"
