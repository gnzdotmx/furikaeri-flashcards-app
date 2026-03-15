from __future__ import annotations

import os
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request


@dataclass
class Bucket:
    tokens: float
    last: float


class TokenBucketLimiter:
    """In-memory token bucket per key (per-process)."""

    def __init__(self, *, capacity: float, refill_per_sec: float):
        self.capacity = float(capacity)
        self.refill = float(refill_per_sec)
        self.buckets: dict[str, Bucket] = {}

    def allow(self, key: str, cost: float = 1.0) -> bool:
        now = time.monotonic()
        b = self.buckets.get(key)
        if not b:
            b = Bucket(tokens=self.capacity, last=now)
            self.buckets[key] = b
        # refill
        dt = max(0.0, now - b.last)
        b.tokens = min(self.capacity, b.tokens + dt * self.refill)
        b.last = now
        if b.tokens >= cost:
            b.tokens -= cost
            return True
        return False

    def reset(self) -> None:
        """Clear all buckets (for tests)."""
        self.buckets.clear()


IMPORT_LIMITER = TokenBucketLimiter(capacity=5, refill_per_sec=0.1)
TTS_LIMITER = TokenBucketLimiter(capacity=10, refill_per_sec=0.5)
AUTH_LIMITER = TokenBucketLimiter(capacity=10, refill_per_sec=0.2)


def client_ip(request: Request) -> str:
    if request.client:
        return request.client.host or "unknown"
    return "unknown"


async def rate_limit_middleware(request: Request, call_next):
    if os.environ.get("TESTING") == "1":
        return await call_next(request)
    path = request.url.path or ""
    ip = client_ip(request)

    if (path.startswith("/imports/") or path.startswith("/api/imports/")) and request.method in ("POST", "PUT"):
        if not IMPORT_LIMITER.allow(f"import:{ip}", cost=1.0):
            raise HTTPException(status_code=429, detail="rate limited")
    if (path.startswith("/tts") or path.startswith("/api/tts")) and request.method in ("POST", "GET"):
        if not TTS_LIMITER.allow(f"tts:{ip}", cost=1.0):
            raise HTTPException(status_code=429, detail="rate limited")
    if "/auth/register" in path or "/auth/login" in path:
        if request.method == "POST" and not AUTH_LIMITER.allow(f"auth:{ip}", cost=1.0):
            raise HTTPException(status_code=429, detail="rate limited")

    return await call_next(request)

