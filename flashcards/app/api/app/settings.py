import os
from dataclasses import dataclass
from pathlib import Path


def _getenv(name: str, default: str) -> str:
    v = os.getenv(name, default)
    return v if v is not None else default


def _getenv_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


# CSV upload size cap (env CSV_UPLOAD_MAX_BYTES), clamped 1–500 MiB.
_DEFAULT_CSV_UPLOAD_MAX_BYTES = 50 * 1024 * 1024  # 50 MiB
_CSV_UPLOAD_MIN_BYTES = 1024 * 1024  # 1 MiB
_CSV_UPLOAD_MAX_BYTES_CAP = 500 * 1024 * 1024  # 500 MiB


def _parse_csv_upload_max_bytes() -> int:
    raw = os.getenv("CSV_UPLOAD_MAX_BYTES", "").strip()
    if not raw:
        return _DEFAULT_CSV_UPLOAD_MAX_BYTES
    try:
        value = int(raw)
    except ValueError:
        return _DEFAULT_CSV_UPLOAD_MAX_BYTES
    return max(_CSV_UPLOAD_MIN_BYTES, min(value, _CSV_UPLOAD_MAX_BYTES_CAP))


@dataclass(frozen=True)
class Settings:
    app_env: str
    sqlite_path: str
    data_dir: str
    audio_cache_dir: str
    cors_allow_origins: list[str]
    serve_web: bool
    jwt_secret: str
    jwt_algorithm: str
    csv_upload_max_bytes: int


def load_settings() -> Settings:
    cors_raw = _getenv("CORS_ALLOW_ORIGINS", "")
    origins = [o.strip() for o in cors_raw.split(",") if o.strip()]
    data_dir = _getenv("DATA_DIR", "/data")
    sqlite_path = _getenv("SQLITE_PATH", f"{data_dir}/flashcards.sqlite")
    # Absolute path so all workers see the same file
    sqlite_path = str(Path(sqlite_path).resolve())
    jwt_secret = os.getenv("JWT_SECRET", "").strip()
    if not jwt_secret:
        raise ValueError(
            "JWT_SECRET environment variable is required. "
            "Set it to a strong secret (at least 32 characters). See .env.example."
        )
    return Settings(
        app_env=_getenv("APP_ENV", "development"),
        sqlite_path=sqlite_path,
        data_dir=data_dir,
        audio_cache_dir=_getenv("AUDIO_CACHE_DIR", f"{data_dir}/audio_cache"),
        cors_allow_origins=origins,
        serve_web=_getenv_bool("SERVE_WEB", False),
        jwt_secret=jwt_secret,
        jwt_algorithm=_getenv("JWT_ALGORITHM", "HS256"),
        csv_upload_max_bytes=_parse_csv_upload_max_bytes(),
    )


def get_settings() -> Settings:
    """FastAPI dependency: returns current Settings (used by route handlers)."""
    return load_settings()

