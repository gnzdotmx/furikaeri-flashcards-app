"""Pytest configuration. Ensures JWT_SECRET is set for tests that use settings or create_app."""

import os


def pytest_configure():
    """Set JWT_SECRET for the test session if not already set (required by app.settings)."""
    if not os.getenv("JWT_SECRET", "").strip():
        os.environ["JWT_SECRET"] = "test-jwt-secret-at-least-32-bytes-for-hs256"
