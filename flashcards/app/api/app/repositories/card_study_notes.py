"""Per-user study notes attached to flashcards (distinct from imported `notes` rows)."""

from .base import BaseRepository


class CardStudyNoteRepository(BaseRepository):
    def get_for_user(self, *, user_id: str, card_id: str) -> dict | None:
        row = self._conn.execute(
            """
            SELECT user_id, card_id, body, updated_at
            FROM card_study_notes
            WHERE user_id = ? AND card_id = ?;
            """,
            (user_id, card_id),
        ).fetchone()
        return dict(row) if row else None

    def upsert(self, *, user_id: str, card_id: str, body: str) -> dict:
        self._conn.execute(
            """
            INSERT INTO card_study_notes(user_id, card_id, body, updated_at)
            VALUES(?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            ON CONFLICT(user_id, card_id) DO UPDATE SET
              body = excluded.body,
              updated_at = excluded.updated_at;
            """,
            (user_id, card_id, body),
        )
        row = self._conn.execute(
            """
            SELECT user_id, card_id, body, updated_at
            FROM card_study_notes
            WHERE user_id = ? AND card_id = ?;
            """,
            (user_id, card_id),
        ).fetchone()
        if not row:
            raise RuntimeError("card_study_notes upsert failed")
        return dict(row)

    def delete_for_user(self, *, user_id: str, card_id: str) -> bool:
        cur = self._conn.execute(
            "DELETE FROM card_study_notes WHERE user_id = ? AND card_id = ?;",
            (user_id, card_id),
        )
        return int(cur.rowcount or 0) > 0
