"""Tests for app.middleware.rate_limit. Skip entire module if fastapi not installed."""

import asyncio
import os
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

try:
    from app.middleware.rate_limit import (
        Bucket,
        TokenBucketLimiter,
        client_ip,
    )
except ImportError:
    pytest.skip("fastapi not installed", allow_module_level=True)


class TestBucket:
    def test_bucket_dataclass(self) -> None:
        b = Bucket(tokens=5.0, last=100.0)
        assert b.tokens == 5.0
        assert b.last == 100.0


class TestTokenBucketLimiter:
    def test_allow_first_call_uses_capacity(self) -> None:
        limiter = TokenBucketLimiter(capacity=3.0, refill_per_sec=1.0)
        assert limiter.allow("k1") is True
        assert limiter.allow("k1") is True
        assert limiter.allow("k1") is True
        assert limiter.allow("k1") is False

    def test_allow_different_keys_independent(self) -> None:
        limiter = TokenBucketLimiter(capacity=1.0, refill_per_sec=1.0)
        assert limiter.allow("a") is True
        assert limiter.allow("a") is False
        assert limiter.allow("b") is True

    def test_allow_refill_after_time(self) -> None:
        limiter = TokenBucketLimiter(capacity=2.0, refill_per_sec=10.0)  # 10 per sec
        assert limiter.allow("k") is True
        assert limiter.allow("k") is True
        assert limiter.allow("k") is False
        time.sleep(0.15)  # 1.5 tokens
        assert limiter.allow("k") is True

    def test_allow_cost(self) -> None:
        limiter = TokenBucketLimiter(capacity=5.0, refill_per_sec=0.0)
        assert limiter.allow("k", cost=3.0) is True
        assert limiter.allow("k", cost=3.0) is False
        assert limiter.allow("k", cost=2.0) is True


def test_client_ip_with_host() -> None:
    request = MagicMock()
    request.client = MagicMock()
    request.client.host = "192.168.1.1"
    assert client_ip(request) == "192.168.1.1"


def test_client_ip_none_host_returns_unknown() -> None:
    request = MagicMock()
    request.client = MagicMock()
    request.client.host = None
    assert client_ip(request) == "unknown"


def test_client_ip_no_client_returns_unknown() -> None:
    request = MagicMock()
    request.client = None
    assert client_ip(request) == "unknown"


def test_rate_limit_middleware_passes_through_unlimited_path() -> None:
    pytest.importorskip("fastapi")
    from fastapi import HTTPException  # noqa: F401

    from app.middleware.rate_limit import rate_limit_middleware

    request = MagicMock()
    request.url = MagicMock()
    request.url.path = "/health"
    request.method = "GET"
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    call_next = AsyncMock(return_value=MagicMock())

    async def run():
        return await rate_limit_middleware(request, call_next)

    response = asyncio.run(run())
    call_next.assert_called_once_with(request)
    assert response == call_next.return_value


def test_rate_limit_middleware_imports_post_can_allow() -> None:
    pytest.importorskip("fastapi")
    from app.middleware.rate_limit import rate_limit_middleware

    request = MagicMock()
    request.url = MagicMock()
    request.url.path = "/api/imports/upload"
    request.method = "POST"
    request.client = MagicMock()
    request.client.host = "1.2.3.4"
    call_next = AsyncMock(return_value=MagicMock())
    response = asyncio.run(rate_limit_middleware(request, call_next))
    call_next.assert_called_once()
    assert response is not None


def test_rate_limit_middleware_imports_exhausted_returns_429() -> None:
    pytest.importorskip("fastapi")
    from fastapi import HTTPException

    from app.middleware import rate_limit
    from app.middleware.rate_limit import rate_limit_middleware

    # Ensure middleware enforces limit (TESTING=1 bypass would skip this)
    old_testing = os.environ.pop("TESTING", None)
    try:
        # Exhaust the limiter for a specific IP
        limiter = rate_limit.IMPORT_LIMITER
        for _ in range(6):
            limiter.allow("import:5.5.5.5")
        request = MagicMock()
        request.url = MagicMock()
        request.url.path = "/imports/upload"
        request.method = "POST"
        request.client = MagicMock()
        request.client.host = "5.5.5.5"
        call_next = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(rate_limit_middleware(request, call_next))
        assert exc_info.value.status_code == 429
        assert "rate limited" in str(exc_info.value.detail).lower()
        call_next.assert_not_called()
    finally:
        if old_testing is not None:
            os.environ["TESTING"] = old_testing


def test_rate_limit_middleware_imports_put_can_allow() -> None:
    """PUT to /imports/ or /api/imports/ is rate limited like POST."""
    pytest.importorskip("fastapi")
    from app.middleware.rate_limit import rate_limit_middleware

    request = MagicMock()
    request.url = MagicMock()
    request.url.path = "/api/imports/something"
    request.method = "PUT"
    request.client = MagicMock()
    request.client.host = "10.0.0.1"
    call_next = AsyncMock(return_value=MagicMock())
    response = asyncio.run(rate_limit_middleware(request, call_next))
    call_next.assert_called_once_with(request)
    assert response == call_next.return_value


def test_rate_limit_middleware_tts_get_can_allow() -> None:
    """GET to /tts or /api/tts is rate limited and can allow under limit."""
    pytest.importorskip("fastapi")
    from app.middleware.rate_limit import rate_limit_middleware

    request = MagicMock()
    request.url = MagicMock()
    request.url.path = "/api/tts"
    request.method = "GET"
    request.client = MagicMock()
    request.client.host = "192.168.0.1"
    call_next = AsyncMock(return_value=MagicMock())
    response = asyncio.run(rate_limit_middleware(request, call_next))
    call_next.assert_called_once_with(request)
    assert response == call_next.return_value


def test_rate_limit_middleware_tts_post_can_allow() -> None:
    """POST to /tts is rate limited and can allow under limit."""
    pytest.importorskip("fastapi")
    from app.middleware.rate_limit import rate_limit_middleware

    request = MagicMock()
    request.url = MagicMock()
    request.url.path = "/tts"
    request.method = "POST"
    request.client = MagicMock()
    request.client.host = "192.168.0.2"
    call_next = AsyncMock(return_value=MagicMock())
    response = asyncio.run(rate_limit_middleware(request, call_next))
    call_next.assert_called_once_with(request)
    assert response == call_next.return_value


def test_rate_limit_middleware_tts_exhausted_returns_429() -> None:
    """When TTS limiter is exhausted for the client IP, middleware returns 429."""
    pytest.importorskip("fastapi")
    from fastapi import HTTPException

    from app.middleware import rate_limit
    from app.middleware.rate_limit import rate_limit_middleware

    # Ensure middleware enforces limit (TESTING=1 bypass would skip this)
    old_testing = os.environ.pop("TESTING", None)
    try:
        limiter = rate_limit.TTS_LIMITER
        tts_ip = "7.7.7.7"
        for _ in range(11):
            limiter.allow(f"tts:{tts_ip}")
        request = MagicMock()
        request.url = MagicMock()
        request.url.path = "/api/tts"
        request.method = "GET"
        request.client = MagicMock()
        request.client.host = tts_ip
        call_next = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(rate_limit_middleware(request, call_next))
        assert exc_info.value.status_code == 429
        assert "rate limited" in str(exc_info.value.detail).lower()
        call_next.assert_not_called()
    finally:
        if old_testing is not None:
            os.environ["TESTING"] = old_testing


def test_rate_limit_middleware_path_none_passes_through() -> None:
    """When request.url.path is None, path is treated as '' and no rate limit applies."""
    pytest.importorskip("fastapi")
    from app.middleware.rate_limit import rate_limit_middleware

    request = MagicMock()
    request.url = MagicMock()
    request.url.path = None
    request.method = "GET"
    request.client = MagicMock()
    request.client.host = "1.2.3.4"
    call_next = AsyncMock(return_value=MagicMock())
    response = asyncio.run(rate_limit_middleware(request, call_next))
    call_next.assert_called_once_with(request)
    assert response == call_next.return_value
