"""JWT creation and verification for auth."""

import time
import uuid

import jwt

DEFAULT_EXPIRY_SECONDS = 7 * 24 * 3600  # 7 days


def create_token(
    user_id: str,
    secret: str,
    algorithm: str = "HS256",
    expires_seconds: int = DEFAULT_EXPIRY_SECONDS,
    jti: str | None = None,
) -> str:
    """Build JWT with sub=user_id, jti, exp. Returns encoded string."""
    now = int(time.time())
    if jti is None:
        jti = uuid.uuid4().hex
    payload = {"sub": user_id, "jti": jti, "iat": now, "exp": now + expires_seconds}
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_token(token: str, secret: str, algorithm: str = "HS256") -> dict | None:
    """Verify and decode JWT. Returns payload dict or None if invalid."""
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
        return payload
    except jwt.PyJWTError:
        return None
