import uuid

from .base import BaseRepository


class UserRepository(BaseRepository):
    def create_user(self, user_id: str | None = None) -> str:
        uid = user_id or str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO users(id, created_at) VALUES(?, strftime('%Y-%m-%dT%H:%M:%fZ','now'));",
            (uid,),
        )
        return uid

    def create_user_with_password(
        self,
        username: str,
        email: str,
        password_hash: str,
        user_id: str | None = None,
    ) -> str:
        """Create user; username and email must be unique."""
        uid = user_id or str(uuid.uuid4())
        self._conn.execute(
            """
            INSERT INTO users(id, created_at, username, email, password_hash)
            VALUES(?, strftime('%Y-%m-%dT%H:%M:%fZ','now'), ?, ?, ?);
            """,
            (uid, username, email.lower(), password_hash),
        )
        return uid

    def get_user(self, user_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT id, created_at, username, email FROM users WHERE id = ?;",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None

    def get_user_by_username(self, username: str) -> dict | None:
        row = self._conn.execute(
            "SELECT id, created_at, username, email, password_hash FROM users WHERE username = ?;",
            (username,),
        ).fetchone()
        return dict(row) if row else None

    def get_user_by_email(self, email: str) -> dict | None:
        row = self._conn.execute(
            "SELECT id, created_at, username, email, password_hash FROM users WHERE email = ?;",
            (email.lower(),),
        ).fetchone()
        return dict(row) if row else None

    def ensure_single_user(self) -> str:
        row = self._conn.execute("SELECT id FROM users ORDER BY created_at ASC LIMIT 1;").fetchone()
        if row:
            return str(row["id"])
        return self.create_user()

    def get_settings(self, user_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT id, new_cards_per_day, target_retention, daily_goal_reviews FROM users WHERE id = ?;",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None

    def update_settings(self, user_id: str, *, daily_goal_reviews: int | None = None) -> None:
        """Update settings; only provided fields are updated."""
        if daily_goal_reviews is not None:
            self._conn.execute(
                "UPDATE users SET daily_goal_reviews = ? WHERE id = ?;",
                (daily_goal_reviews if daily_goal_reviews > 0 else None, user_id),
            )

