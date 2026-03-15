"""Tests for app.settings (load_settings, get_settings dependency)."""

import os

from app.settings import Settings, get_settings, load_settings


def test_load_settings_returns_settings_instance():
    """load_settings() returns a Settings dataclass with expected attributes."""
    settings = load_settings()
    assert isinstance(settings, Settings)
    assert hasattr(settings, "sqlite_path")
    assert hasattr(settings, "data_dir")
    assert hasattr(settings, "audio_cache_dir")
    assert hasattr(settings, "app_env")
    assert hasattr(settings, "cors_allow_origins")
    assert hasattr(settings, "serve_web")
    assert hasattr(settings, "csv_upload_max_bytes")
    assert isinstance(settings.cors_allow_origins, list)
    assert isinstance(settings.csv_upload_max_bytes, int)
    assert settings.csv_upload_max_bytes >= 1024 * 1024


def test_load_settings_resolves_sqlite_path():
    """SQLITE_PATH is resolved to an absolute path."""
    settings = load_settings()
    assert os.path.isabs(settings.sqlite_path)
    assert settings.sqlite_path.endswith(".sqlite") or "flashcards" in settings.sqlite_path


def test_get_settings_returns_same_type_as_load_settings():
    """get_settings() is the dependency wrapper and returns Settings (for FastAPI Depends)."""
    settings = get_settings()
    assert isinstance(settings, Settings)
    assert settings.sqlite_path == load_settings().sqlite_path


def test_get_settings_callable_for_fastapi_depends():
    """get_settings() is a callable taking no args, for use with FastAPI Depends(get_settings)."""
    # FastAPI calls the dependency; we just ensure it's callable and returns Settings
    assert callable(get_settings)
    out = get_settings()
    assert isinstance(out, Settings)


def test_csv_upload_max_bytes_from_env():
    """CSV_UPLOAD_MAX_BYTES is read from env and clamped to 1 MiB–500 MiB."""
    old = os.environ.get("CSV_UPLOAD_MAX_BYTES")
    try:
        os.environ["CSV_UPLOAD_MAX_BYTES"] = "2097152"
        s = load_settings()
        assert s.csv_upload_max_bytes == 2097152
        os.environ["CSV_UPLOAD_MAX_BYTES"] = "1"
        s = load_settings()
        assert s.csv_upload_max_bytes == 1024 * 1024
        os.environ.pop("CSV_UPLOAD_MAX_BYTES", None)
        s = load_settings()
        assert s.csv_upload_max_bytes == 50 * 1024 * 1024
    finally:
        if old is None:
            os.environ.pop("CSV_UPLOAD_MAX_BYTES", None)
        else:
            os.environ["CSV_UPLOAD_MAX_BYTES"] = old
