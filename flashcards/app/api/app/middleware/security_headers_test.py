"""Tests for app.middleware.security_headers. Require fastapi (e.g. run via make test)."""

import asyncio
from unittest.mock import MagicMock

import pytest


def test_security_headers_adds_baseline_headers() -> None:
    pytest.importorskip("fastapi")
    from app.middleware.security_headers import security_headers_middleware
    request = MagicMock()
    request.app = MagicMock()
    request.app.state = MagicMock()
    request.app.state.serve_web = False

    response = MagicMock()
    response.headers = {}

    async def call_next(req):
        return response

    result = asyncio.run(security_headers_middleware(request, call_next))
    assert result is response
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("Referrer-Policy") == "no-referrer"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert "Permissions-Policy" in response.headers


def test_security_headers_serve_web_adds_csp() -> None:
    pytest.importorskip("fastapi")
    from app.middleware.security_headers import security_headers_middleware

    request = MagicMock()
    request.app = MagicMock()
    request.app.state = MagicMock()
    request.app.state.serve_web = True

    response = MagicMock()
    response.headers = {}

    async def call_next(req):
        return response

    asyncio.run(security_headers_middleware(request, call_next))
    csp = response.headers.get("Content-Security-Policy")
    assert csp is not None
    assert "default-src 'self'" in csp
    assert "script-src" in csp


def test_security_headers_setdefault_does_not_overwrite() -> None:
    pytest.importorskip("fastapi")
    from app.middleware.security_headers import security_headers_middleware

    request = MagicMock()
    request.app = MagicMock()
    request.app.state = MagicMock()
    request.app.state.serve_web = False

    response = MagicMock()
    response.headers = {"X-Content-Type-Options": "custom"}

    async def call_next(req):
        return response

    asyncio.run(security_headers_middleware(request, call_next))
    assert response.headers["X-Content-Type-Options"] == "custom"
