"""Auth helpers: bearer/session token, current user id (set by auth middleware)."""

from fastapi import Depends, Request

from ..routes.dependencies import get_sqlite_path


def get_bearer_token(request: Request) -> str | None:
    """Authorization header Bearer token, or None."""
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return None
    return auth[7:].strip() or None


SESSION_COOKIE_NAME = "furikaeri_session"


def get_session_token(request: Request) -> str | None:
    """Bearer token from header, or session cookie if same-origin."""
    token = get_bearer_token(request)
    if token:
        return token
    return request.cookies.get(SESSION_COOKIE_NAME) or None


def get_current_user_id(request: Request, _sqlite_path: str = Depends(get_sqlite_path)) -> str:
    """user_id from request.state (set by auth middleware). Raises 401 if not authenticated."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id
