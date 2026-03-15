"""Auth sessions by JWT jti (validated per request)."""

import time

from .base import BaseRepository


class AuthSessionRepository(BaseRepository):
    """Auth sessions keyed by JWT jti."""

    def create(self, jti: str, user_id: str, expires_at: int) -> None:
        """Insert session (created_at = now)."""
        now = int(time.time())
        self._conn.execute(
            "INSERT INTO auth_sessions (jti, user_id, created_at, expires_at) VALUES (?, ?, ?, ?);",
            (jti, user_id, now, expires_at),
        )

    def get_valid(self, jti: str) -> dict | None:
        """Session row if jti valid and not expired, else None."""
        now = int(time.time())
        row = self._conn.execute(
            "SELECT jti, user_id, created_at, expires_at FROM auth_sessions WHERE jti = ? AND expires_at > ?;",
            (jti, now),
        ).fetchone()
        return dict(row) if row else None

    def delete_by_jti(self, jti: str) -> bool:
        """Delete session by jti. Returns True if a row was deleted."""
        cur = self._conn.execute("DELETE FROM auth_sessions WHERE jti = ?;", (jti,))
        return cur.rowcount > 0
