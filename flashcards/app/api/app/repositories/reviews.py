from .base import BaseRepository


class ReviewRepository(BaseRepository):
    def upsert_review_state(
        self,
        *,
        card_id: str,
        user_id: str,
        due_at: str,
        stability: float = 0.0,
        difficulty: float = 0.0,
        last_rating: str | None = None,
        lapses: int = 0,
        reps: int = 0,
        avg_time_ms: int = 0,
        streak: int = 0,
        leech_flag: int = 0,
        learning_step: int = -1,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO review_state(
              card_id, user_id, due_at, stability, difficulty, last_rating, lapses, reps, avg_time_ms, streak, leech_flag, learning_step,
              created_at, updated_at
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'), strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            ON CONFLICT(card_id, user_id) DO UPDATE SET
              due_at=excluded.due_at,
              stability=excluded.stability,
              difficulty=excluded.difficulty,
              last_rating=excluded.last_rating,
              lapses=excluded.lapses,
              reps=excluded.reps,
              avg_time_ms=excluded.avg_time_ms,
              streak=excluded.streak,
              leech_flag=excluded.leech_flag,
              learning_step=excluded.learning_step,
              updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now');
            """,
            (
                card_id,
                user_id,
                due_at,
                float(stability),
                float(difficulty),
                last_rating,
                int(lapses),
                int(reps),
                int(avg_time_ms),
                int(streak),
                int(leech_flag),
                int(learning_step),
            ),
        )

    def get_review_state(self, card_id: str, user_id: str) -> dict | None:
        row = self._conn.execute(
            """
            SELECT card_id, user_id, due_at, stability, difficulty, last_rating, lapses, reps, avg_time_ms, streak, leech_flag,
                   COALESCE(learning_step, -1) AS learning_step, COALESCE(suspended, 0) AS suspended, created_at, updated_at
            FROM review_state
            WHERE card_id = ? AND user_id = ?;
            """,
            (card_id, user_id),
        ).fetchone()
        return dict(row) if row else None

    def set_suspended(self, *, card_id: str, user_id: str, suspended: bool) -> bool:
        """Set suspended flag (1 = exclude from sessions). Returns True if a row was updated."""
        cur = self._conn.execute(
            """
            UPDATE review_state
            SET suspended = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
            WHERE card_id = ? AND user_id = ?;
            """,
            (1 if suspended else 0, card_id, user_id),
        )
        return int(cur.rowcount or 0) > 0

