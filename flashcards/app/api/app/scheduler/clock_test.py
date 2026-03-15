"""Tests for app.scheduler.clock."""

from datetime import datetime, timezone

from app.scheduler.clock import isoformat_z, utcnow


def test_utcnow_returns_aware_utc() -> None:
    now = utcnow()
    assert now.tzinfo is timezone.utc
    assert now.tzinfo is not None


def test_utcnow_recent() -> None:
    before = datetime.now(timezone.utc)
    now = utcnow()
    after = datetime.now(timezone.utc)
    assert before <= now <= after


def test_isoformat_z_utc_suffix() -> None:
    dt = datetime(2026, 2, 8, 12, 30, 45, 123000, tzinfo=timezone.utc)
    out = isoformat_z(dt)
    assert out.endswith("Z")
    assert "+00:00" not in out
    assert "2026-02-08" in out
    assert "12:30:45.123" in out


def test_isoformat_z_converts_to_utc() -> None:
    from datetime import timedelta

    # UTC+1
    tz = timezone(timedelta(hours=1))
    dt = datetime(2026, 2, 8, 13, 0, 0, 0, tzinfo=tz)
    out = isoformat_z(dt)
    assert out.endswith("Z")
    # 13:00 UTC+1 = 12:00 UTC
    assert "12:00:00" in out
