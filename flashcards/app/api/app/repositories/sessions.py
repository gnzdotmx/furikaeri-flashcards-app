import uuid

from .base import BaseRepository


class SessionRepository(BaseRepository):
    def create_session(
        self,
        *,
        user_id: str,
        deck_id: str,
        mode: str,
        new_limit: int,
        include_listening: bool = True,
    ) -> str:
        sid = str(uuid.uuid4())
        self._conn.execute(
            """
            INSERT INTO study_sessions(id, user_id, deck_id, mode, new_limit, new_shown, include_listening, created_at)
            VALUES(?, ?, ?, ?, ?, 0, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'));
            """,
            (sid, user_id, deck_id, mode, int(new_limit), 1 if include_listening else 0),
        )
        return sid

    def get_session(self, session_id: str) -> dict | None:
        row = self._conn.execute(
            """
            SELECT id, user_id, deck_id, mode, new_limit, new_shown, created_at, ended_at,
                   COALESCE(include_listening, 1) AS include_listening
            FROM study_sessions WHERE id = ?;
            """,
            (session_id,),
        ).fetchone()
        return dict(row) if row else None

    def mark_seen(self, *, session_id: str, card_id: str) -> None:
        self._conn.execute(
            """
            INSERT OR IGNORE INTO session_seen(session_id, card_id, seen_at)
            VALUES(?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'));
            """,
            (session_id, card_id),
        )

    def is_seen(self, *, session_id: str, card_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM session_seen WHERE session_id = ? AND card_id = ?;",
            (session_id, card_id),
        ).fetchone()
        return bool(row)

    def increment_new_shown(self, *, session_id: str) -> None:
        self._conn.execute(
            "UPDATE study_sessions SET new_shown = new_shown + 1 WHERE id = ?;",
            (session_id,),
        )

    def end_session(self, *, session_id: str) -> None:
        self._conn.execute(
            "UPDATE study_sessions SET ended_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id = ? AND ended_at IS NULL;",
            (session_id,),
        )

