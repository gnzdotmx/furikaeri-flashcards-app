"""Register, login, logout, me."""

import re
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..auth import get_current_user_id, hash_password, verify_password
from ..auth.dependencies import SESSION_COOKIE_NAME
from ..auth.jwt_utils import create_token, DEFAULT_EXPIRY_SECONDS
from ..db import connection, transaction
from ..repositories.auth_sessions import AuthSessionRepository
from ..repositories.users import UserRepository
from ..settings import Settings, get_settings
from .dependencies import get_sqlite_path

SESSION_COOKIE_MAX_AGE = DEFAULT_EXPIRY_SECONDS  # match JWT expiry

router = APIRouter()

USERNAME_MIN = 2
USERNAME_MAX = 32
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
EMAIL_MAX = 254
# Basic email shape: local@domain.tld, 2+ char TLD
EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$"
)
PASSWORD_MIN = 8
PASSWORD_MAX = 128


class RegisterReq(BaseModel):
    username: str = Field(..., min_length=USERNAME_MIN, max_length=USERNAME_MAX)
    email: str = Field(..., max_length=EMAIL_MAX)
    password: str = Field(..., min_length=PASSWORD_MIN, max_length=PASSWORD_MAX)


class LoginReq(BaseModel):
    username: str = Field(..., min_length=1, max_length=USERNAME_MAX)
    password: str = Field(..., min_length=1, max_length=PASSWORD_MAX)


def _validate_username(username: str) -> None:
    if not USERNAME_PATTERN.match(username):
        raise HTTPException(
            status_code=400,
            detail="Username may only contain letters, numbers, underscore and hyphen.",
        )


def _validate_email(email: str) -> None:
    if not email or len(email) > EMAIL_MAX:
        raise HTTPException(status_code=400, detail="Invalid email format.")
    if not EMAIL_PATTERN.match(email):
        raise HTTPException(status_code=400, detail="Invalid email format.")


def _user_public(user_row: dict) -> dict:
    """Strip to id, username, email (no password_hash)."""
    return {
        "id": user_row["id"],
        "username": user_row.get("username"),
        "email": user_row.get("email"),
    }


def _auth_response(
    user_id: str,
    user_row: dict,
    settings: Settings,
    sqlite_path: str,
) -> dict:
    """Create auth_sessions row, build JWT, return {access_token, token_type, user}."""
    jti = uuid.uuid4().hex
    now = int(time.time())
    expires_at = now + DEFAULT_EXPIRY_SECONDS
    token = create_token(
        user_id,
        settings.jwt_secret,
        settings.jwt_algorithm,
        expires_seconds=DEFAULT_EXPIRY_SECONDS,
        jti=jti,
    )
    with connection(sqlite_path) as conn:
        with transaction(conn):
            AuthSessionRepository(conn).create(jti, user_id, expires_at)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": _user_public(user_row),
    }


def _auth_response_with_cookie(
    body: dict,
    token: str,
    settings: Settings,
) -> JSONResponse:
    """JSON response plus HttpOnly session cookie (middleware accepts cookie or header)."""
    response = JSONResponse(content=body)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=settings.app_env == "production",
        path="/",
    )
    return response


@router.post("/auth/register")
def register(
    req: RegisterReq,
    sqlite_path: str = Depends(get_sqlite_path),
    settings: Settings = Depends(get_settings),
):
    """Create user, create session, return JWT and user."""
    _validate_username(req.username)
    _validate_email(req.email)

    with connection(sqlite_path) as conn:
        repo = UserRepository(conn)
        if repo.get_user_by_username(req.username):
            raise HTTPException(status_code=409, detail="Username already taken.")
        if repo.get_user_by_email(req.email):
            raise HTTPException(status_code=409, detail="Email already registered.")

        with transaction(conn):
            user_id = repo.create_user_with_password(
                username=req.username,
                email=req.email,
                password_hash=hash_password(req.password),
            )
        user = repo.get_user(user_id)
        assert user is not None

    body = _auth_response(user_id, user, settings, sqlite_path)
    return _auth_response_with_cookie(body, body["access_token"], settings)


@router.post("/auth/login")
def login(
    req: LoginReq,
    sqlite_path: str = Depends(get_sqlite_path),
    settings: Settings = Depends(get_settings),
):
    """Validate credentials, create session, return JWT and user."""
    with connection(sqlite_path) as conn:
        repo = UserRepository(conn)
        user = repo.get_user_by_username(req.username)
        if not user or not user.get("password_hash"):
            raise HTTPException(status_code=401, detail="Invalid username or password.")
        if not verify_password(req.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid username or password.")
        user_id = user["id"]

    body = _auth_response(user_id, user, settings, sqlite_path)
    return _auth_response_with_cookie(body, body["access_token"], settings)


@router.get("/auth/me")
def me(
    user_id: str = Depends(get_current_user_id),
    sqlite_path: str = Depends(get_sqlite_path),
):
    """Current user profile (requires auth)."""
    with connection(sqlite_path) as conn:
        user = UserRepository(conn).get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return _user_public(user)


@router.post("/auth/logout")
def logout(
    request: Request,
    sqlite_path: str = Depends(get_sqlite_path),
):
    """Delete session by jti, clear cookie."""
    jti = getattr(request.state, "session_jti", None)
    if not jti:
        raise HTTPException(status_code=401, detail="Not authenticated")
    with connection(sqlite_path) as conn:
        AuthSessionRepository(conn).delete_by_jti(jti)
        conn.commit()
    response = JSONResponse(content={})
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return response
