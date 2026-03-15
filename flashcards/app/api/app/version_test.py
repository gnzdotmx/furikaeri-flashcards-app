"""Tests for app.version."""

from app.version import APP_VERSION


def test_app_version_is_string() -> None:
    assert isinstance(APP_VERSION, str)
    assert len(APP_VERSION) >= 1


def test_app_version_semver_like() -> None:
    parts = APP_VERSION.split(".")
    assert len(parts) >= 1
    for p in parts:
        assert p.isdigit() or (p and p[0].isdigit())
