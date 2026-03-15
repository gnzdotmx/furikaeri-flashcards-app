"""Route dependencies: sqlite path, settings."""

from fastapi import Depends, Request

from ..settings import Settings, get_settings


def get_sqlite_path(request: Request, settings: Settings = Depends(get_settings)) -> str:
    """DB path from app.state or settings (tests can inject via app.state)."""
    return getattr(request.app.state, "sqlite_path", None) or settings.sqlite_path
