"""Auth middleware: for /api routes (except public), require valid JWT and auth_sessions row."""

from __future__ import annotations

from fastapi import Request, Response

from ..auth.dependencies import get_session_token
from ..auth.jwt_utils import decode_token
from ..db import connection
from ..repositories.auth_sessions import AuthSessionRepository
from ..settings import get_settings


_PUBLIC_PATHS = frozenset({
    "/health",
    "/api/health",
    "/api/version",
    "/api/auth/register",
    "/api/auth/login",
})


def _is_public(path: str) -> bool:
    if path in _PUBLIC_PATHS:
        return True
    return False


async def auth_session_middleware(request: Request, call_next) -> Response:
    """Check JWT and auth_sessions; set request.state.user_id and session_jti on success."""
    path = (request.url.path or "").strip()
    if not path.startswith("/api"):
        return await call_next(request)
    if _is_public(path):
        return await call_next(request)

    token = get_session_token(request)
    if not token:
        return Response(
            content='{"detail":"Not authenticated"}',
            status_code=401,
            media_type="application/json",
        )
    settings = get_settings()
    payload = decode_token(token, settings.jwt_secret, settings.jwt_algorithm)
    if not payload:
        return Response(
            content='{"detail":"Invalid or expired token"}',
            status_code=401,
            media_type="application/json",
        )
    jti = payload.get("jti")
    user_id = payload.get("sub")
    if not isinstance(jti, str) or not jti or not isinstance(user_id, str) or not user_id:
        return Response(
            content='{"detail":"Invalid token"}',
            status_code=401,
            media_type="application/json",
        )

    sqlite_path = getattr(request.app.state, "sqlite_path", None) or settings.sqlite_path
    with connection(sqlite_path) as conn:
        repo = AuthSessionRepository(conn)
        session = repo.get_valid(jti)
    if not session or session.get("user_id") != user_id:
        return Response(
            content='{"detail":"Session invalid or expired"}',
            status_code=401,
            media_type="application/json",
        )

    request.state.user_id = user_id
    request.state.session_jti = jti
    return await call_next(request)
