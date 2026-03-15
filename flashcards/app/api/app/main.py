import sys
from pathlib import Path

from fastapi import FastAPI

from .logging_config import configure as configure_logging
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .db import db_health, connection, ensure_db, run_migrations, transaction
from .routes import router
from .settings import load_settings
from .version import APP_VERSION
from .repositories.users import UserRepository
from .middleware.auth_session import auth_session_middleware
from .middleware.rate_limit import rate_limit_middleware
from .middleware.security_headers import security_headers_middleware


def create_app() -> FastAPI:
    configure_logging()
    settings = load_settings()

    app = FastAPI(title="furikaeri-api", version=APP_VERSION)
    app.state.serve_web = settings.serve_web
    app.state.sqlite_path = settings.sqlite_path

    # DB + migrations + default user
    ensure_db(settings.sqlite_path)
    migration_info = run_migrations(settings.sqlite_path)
    with connection(settings.sqlite_path) as conn:
        with transaction(conn):
            UserRepository(conn).ensure_single_user()

    Path(settings.audio_cache_dir).mkdir(parents=True, exist_ok=True)

    # Middleware order: auth session, then rate limit, then security headers
    app.middleware("http")(auth_session_middleware)
    app.middleware("http")(rate_limit_middleware)
    app.middleware("http")(security_headers_middleware)

    cors_origins = list(settings.cors_allow_origins)
    if settings.app_env == "production" and "*" in cors_origins:
        cors_origins = []
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type", "Authorization"],
            max_age=600,
        )

    app.mount("/audio", StaticFiles(directory=settings.audio_cache_dir), name="audio")

    def _health_payload():
        db_info = db_health(settings.sqlite_path)
        if settings.app_env == "production":
            db_info = {**db_info, "path": "<redacted>"}
        return {"status": "ok", "db": db_info, "schema": migration_info}

    def _version_payload():
        return {"app_version": APP_VERSION, "schema": migration_info}

    @app.get("/health")
    def health():
        return _health_payload()

    @app.get("/version")
    def version():
        return _version_payload()

    @app.get("/api/health")
    def api_health():
        return _health_payload()

    @app.get("/api/version")
    def api_version():
        return _version_payload()

    app.include_router(router, prefix="/api")

    # Mount web static last so it doesn't override /health etc.
    if settings.serve_web:
        static_dir = Path(__file__).resolve().parent / "static"
        if static_dir.is_dir():
            app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="web")
    return app


# Lazy app for pytest (avoids DB/paths at collect time)
if "pytest" not in sys.modules:
    app = create_app()
else:
    app = None

