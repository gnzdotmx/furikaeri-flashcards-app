import uuid

from .base import BaseRepository


class CardRepository(BaseRepository):
    def upsert_card(
        self,
        *,
        note_id: str,
        deck_id: str,
        card_type: str,
        front_template: str | None = None,
        back_template: str | None = None,
        tags_json: str = "[]",
        card_id: str | None = None,
    ) -> str:
        cid = card_id or str(uuid.uuid4())
        self._conn.execute(
            """
            INSERT INTO cards(id, note_id, deck_id, card_type, front_template, back_template, tags_json, created_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            ON CONFLICT(note_id, deck_id, card_type) DO UPDATE SET
              front_template=excluded.front_template,
              back_template=excluded.back_template,
              tags_json=excluded.tags_json;
            """,
            (cid, note_id, deck_id, card_type, front_template, back_template, tags_json),
        )
        row = self._conn.execute(
            "SELECT id FROM cards WHERE note_id = ? AND deck_id = ? AND card_type = ?;",
            (note_id, deck_id, card_type),
        ).fetchone()
        return str(row["id"]) if row else cid

    def delete_placeholders_for_note(self, *, note_id: str, deck_id: str) -> int:
        cur = self._conn.execute(
            "DELETE FROM cards WHERE note_id = ? AND deck_id = ? AND card_type LIKE ?;",
            (note_id, deck_id, "%_placeholder"),
        )
        return int(cur.rowcount or 0)

    def delete_cards_for_note_except_types(
        self, *, note_id: str, deck_id: str, keep_card_types: set[str]
    ) -> int:
        """Delete cards for this note+deck whose card_type is not in keep_card_types."""
        if not keep_card_types:
            return 0
        placeholders = ",".join("?" for _ in keep_card_types)
        cur = self._conn.execute(
            f"DELETE FROM cards WHERE note_id = ? AND deck_id = ? AND card_type NOT IN ({placeholders});",
            (note_id, deck_id, *keep_card_types),
        )
        return int(cur.rowcount or 0)

    _GRAMMAR_HIDDEN_TYPES = ("grammar_structure_production", "grammar_cloze")
    _CANDIDATE_LIMIT = 30

    def _excluded_card_types(self, exclude_card_types: tuple[str, ...]) -> tuple[str, ...]:
        """Card types to exclude from session (grammar hidden + optional e.g. vocab_listening)."""
        return self._GRAMMAR_HIDDEN_TYPES + exclude_card_types

    def get_next_due_cards(
        self,
        *,
        deck_id: str,
        user_id: str,
        now_iso: str,
        session_id: str,
        limit: int = _CANDIDATE_LIMIT,
        exclude_card_types: tuple[str, ...] = (),
        label_tag: str | None = None,
    ) -> list[dict]:
        """Graduated due cards not yet seen this session; returns up to limit for random choice."""
        excluded = self._excluded_card_types(exclude_card_types)
        placeholders = ",".join("?" for _ in excluded)
        params: list[object] = [user_id, session_id, deck_id, now_iso, *excluded]
        label_clause = ""
        if label_tag:
            # Exact tag match via json_each (tags_json is JSON array)
            label_clause = " AND EXISTS (SELECT 1 FROM json_each(c.tags_json) AS je WHERE je.value = ?)"
            params.append(label_tag)
        params.append(limit)
        rows = self._conn.execute(
            f"""
            SELECT c.id, c.note_id, c.deck_id, c.card_type, c.front_template, c.back_template, c.tags_json, c.created_at,
                   rs.due_at, rs.stability, rs.difficulty, rs.lapses, rs.reps, rs.avg_time_ms, rs.streak, rs.leech_flag
            FROM cards c
            JOIN review_state rs ON rs.card_id = c.id AND rs.user_id = ?
            LEFT JOIN session_seen ss ON ss.session_id = ? AND ss.card_id = c.id
            WHERE c.deck_id = ? AND rs.due_at <= ? AND ss.card_id IS NULL
              AND (rs.learning_step IS NULL OR rs.learning_step < 0)
              AND COALESCE(rs.suspended, 0) = 0
              AND c.card_type NOT IN ({placeholders}){label_clause}
            ORDER BY rs.due_at ASC
            LIMIT ?;
            """,
            params,
        ).fetchall()
        return [dict(r) for r in rows]

    def get_next_new_cards(
        self,
        *,
        deck_id: str,
        user_id: str,
        session_id: str,
        limit: int = _CANDIDATE_LIMIT,
        exclude_card_types: tuple[str, ...] = (),
        label_tag: str | None = None,
    ) -> list[dict]:
        """New cards not yet seen this session; returns up to limit for random choice."""
        excluded = self._excluded_card_types(exclude_card_types)
        placeholders = ",".join("?" for _ in excluded)
        params: list[object] = [user_id, session_id, deck_id, *excluded]
        label_clause = ""
        if label_tag:
            # Exact tag match via json_each (tags_json is JSON array)
            label_clause = " AND EXISTS (SELECT 1 FROM json_each(c.tags_json) AS je WHERE je.value = ?)"
            params.append(label_tag)
        params.append(limit)
        rows = self._conn.execute(
            f"""
            SELECT c.id, c.note_id, c.deck_id, c.card_type, c.front_template, c.back_template, c.tags_json, c.created_at
            FROM cards c
            LEFT JOIN review_state rs ON rs.card_id = c.id AND rs.user_id = ?
            LEFT JOIN session_seen ss ON ss.session_id = ? AND ss.card_id = c.id
            WHERE c.deck_id = ? AND rs.card_id IS NULL AND ss.card_id IS NULL
              AND c.card_type NOT IN ({placeholders}){label_clause}
            ORDER BY c.created_at ASC
            LIMIT ?;
            """,
            params,
        ).fetchall()
        return [dict(r) for r in rows]

    def get_next_due_cards_with_last_rating(
        self,
        *,
        deck_id: str,
        user_id: str,
        now_iso: str,
        session_id: str,
        last_ratings: tuple[str, ...],
        limit: int = _CANDIDATE_LIMIT,
        exclude_card_types: tuple[str, ...] = (),
        label_tag: str | None = None,
    ) -> list[dict]:
        """Graduated due cards with last_rating in last_ratings, not yet seen; returns up to limit for random choice."""
        if not last_ratings:
            return []
        excluded = self._excluded_card_types(exclude_card_types)
        excl_placeholders = ",".join("?" for _ in excluded)
        rating_placeholders = ",".join("?" for _ in last_ratings)
        params: list[object] = [user_id, session_id, deck_id, now_iso, *excluded, *last_ratings]
        label_clause = ""
        if label_tag:
            # Exact tag match via json_each (tags_json is JSON array)
            label_clause = " AND EXISTS (SELECT 1 FROM json_each(c.tags_json) AS je WHERE je.value = ?)"
            params.append(label_tag)
        params.append(limit)
        rows = self._conn.execute(
            f"""
            SELECT c.id, c.note_id, c.deck_id, c.card_type, c.front_template, c.back_template, c.tags_json, c.created_at,
                   rs.due_at, rs.stability, rs.difficulty, rs.lapses, rs.reps, rs.avg_time_ms, rs.streak, rs.leech_flag
            FROM cards c
            JOIN review_state rs ON rs.card_id = c.id AND rs.user_id = ?
            LEFT JOIN session_seen ss ON ss.session_id = ? AND ss.card_id = c.id
            WHERE c.deck_id = ? AND rs.due_at <= ? AND ss.card_id IS NULL
              AND (rs.learning_step IS NULL OR rs.learning_step < 0)
              AND COALESCE(rs.suspended, 0) = 0
              AND c.card_type NOT IN ({excl_placeholders})
              AND rs.last_rating IN ({rating_placeholders}){label_clause}
            ORDER BY rs.due_at ASC
            LIMIT ?;
            """,
            params,
        ).fetchall()
        return [dict(r) for r in rows]

    def get_next_learning_cards(
        self,
        *,
        deck_id: str,
        user_id: str,
        now_iso: str,
        num_steps: int,
        limit: int = _CANDIDATE_LIMIT,
        exclude_card_types: tuple[str, ...] = (),
        label_tag: str | None = None,
    ) -> list[dict]:
        """Cards in learning (step < num_steps) that are due now. Not filtered by session_seen so they reappear when due."""
        if num_steps <= 0:
            return []
        excluded = self._excluded_card_types(exclude_card_types)
        placeholders = ",".join("?" for _ in excluded)
        params: list[object] = [user_id, deck_id, now_iso, num_steps, *excluded]
        label_clause = ""
        if label_tag:
            # Exact tag match via json_each (tags_json is JSON array)
            label_clause = " AND EXISTS (SELECT 1 FROM json_each(c.tags_json) AS je WHERE je.value = ?)"
            params.append(label_tag)
        params.append(limit)
        rows = self._conn.execute(
            f"""
            SELECT c.id, c.note_id, c.deck_id, c.card_type, c.front_template, c.back_template, c.tags_json, c.created_at,
                   rs.due_at, rs.stability, rs.difficulty, rs.lapses, rs.reps, rs.avg_time_ms, rs.streak, rs.leech_flag
            FROM cards c
            JOIN review_state rs ON rs.card_id = c.id AND rs.user_id = ?
            WHERE c.deck_id = ? AND rs.due_at <= ?
              AND rs.learning_step IS NOT NULL AND rs.learning_step >= 0 AND rs.learning_step < ?
              AND COALESCE(rs.suspended, 0) = 0
              AND c.card_type NOT IN ({placeholders}){label_clause}
            ORDER BY rs.due_at ASC
            LIMIT ?;
            """,
            params,
        ).fetchall()
        return [dict(r) for r in rows]

    def count_due_today(self, *, deck_id: str, user_id: str, start_iso: str, end_iso: str) -> int:
        row = self._conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM cards c
            JOIN review_state rs ON rs.card_id = c.id AND rs.user_id = ?
            WHERE c.deck_id = ? AND rs.due_at >= ? AND rs.due_at < ?
              AND COALESCE(rs.suspended, 0) = 0
              AND c.card_type NOT IN (?, ?);
            """,
            (user_id, deck_id, start_iso, end_iso, *self._GRAMMAR_HIDDEN_TYPES),
        ).fetchone()
        return int(row["n"]) if row else 0

    def count_due_now(self, *, deck_id: str, user_id: str, now_iso: str) -> int:
        row = self._conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM cards c
            JOIN review_state rs ON rs.card_id = c.id AND rs.user_id = ?
            WHERE c.deck_id = ? AND rs.due_at <= ?
              AND COALESCE(rs.suspended, 0) = 0
              AND c.card_type NOT IN (?, ?);
            """,
            (user_id, deck_id, now_iso, *self._GRAMMAR_HIDDEN_TYPES),
        ).fetchone()
        return int(row["n"]) if row else 0

    def count_new_available(self, *, deck_id: str, user_id: str) -> int:
        row = self._conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM cards c
            LEFT JOIN review_state rs ON rs.card_id = c.id AND rs.user_id = ?
            WHERE c.deck_id = ? AND rs.card_id IS NULL
              AND c.card_type NOT IN (?, ?);
            """,
            (user_id, deck_id, *self._GRAMMAR_HIDDEN_TYPES),
        ).fetchone()
        return int(row["n"]) if row else 0

    def list_cards_for_deck(self, deck_id: str, limit: int = 200) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT id, note_id, deck_id, card_type, front_template, back_template, tags_json, created_at
            FROM cards
            WHERE deck_id = ?
            ORDER BY created_at DESC
            LIMIT ?;
            """,
            (deck_id, int(limit)),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_leeches(self, *, deck_id: str, user_id: str, limit: int = 200) -> list[dict]:
        """Cards with leech_flag = 1 for this deck and user; includes front/back and lapse count."""
        rows = self._conn.execute(
            """
            SELECT c.id, c.note_id, c.deck_id, c.card_type, c.front_template, c.back_template, c.tags_json, c.created_at,
                   rs.lapses, rs.leech_flag, COALESCE(rs.suspended, 0) AS suspended
            FROM cards c
            JOIN review_state rs ON rs.card_id = c.id AND rs.user_id = ?
            WHERE c.deck_id = ? AND rs.leech_flag = 1
              AND c.card_type NOT IN (?, ?)
            ORDER BY rs.lapses DESC
            LIMIT ?;
            """,
            (user_id, deck_id, *self._GRAMMAR_HIDDEN_TYPES, int(limit)),
        ).fetchall()
        return [dict(r) for r in rows]

    def count_leeches(self, *, deck_id: str, user_id: str) -> int:
        """Number of cards with leech_flag = 1 in this deck for this user."""
        row = self._conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM cards c
            JOIN review_state rs ON rs.card_id = c.id AND rs.user_id = ?
            WHERE c.deck_id = ? AND rs.leech_flag = 1
              AND c.card_type NOT IN (?, ?);
            """,
            (user_id, deck_id, *self._GRAMMAR_HIDDEN_TYPES),
        ).fetchone()
        return int(row["n"]) if row else 0

    @staticmethod
    def _like_escape(term: str) -> str:
        """Escape % and _ for use in LIKE with ESCAPE '\\'."""
        return (term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_"))

    def search_cards_by_text(self, q: str, limit: int = 80) -> list[dict]:
        """Search cards where front_template or back_template contains q (case-insensitive, LIKE)."""
        if not q or len(q) > 200:
            return []
        pattern = f"%{self._like_escape(q)}%"
        rows = self._conn.execute(
            """
            SELECT c.id, c.note_id, c.deck_id, c.card_type, c.front_template, c.back_template, c.tags_json, c.created_at,
                   d.name AS deck_name
            FROM cards c
            JOIN decks d ON d.id = c.deck_id
            WHERE (c.front_template LIKE ? ESCAPE '\\' OR c.back_template LIKE ? ESCAPE '\\')
            ORDER BY c.created_at DESC
            LIMIT ?;
            """,
            (pattern, pattern, int(limit)),
        ).fetchall()
        return [dict(r) for r in rows]

    def list_labels_for_deck(self, deck_id: str, *, limit: int | None = None) -> list[str]:
        """
        Return distinct label:* tags present in cards for this deck.

        tags_json is stored as JSON array of strings; we parse it server-side and
        collect tags starting with 'label:'. This keeps label handling in one place
        and avoids coupling to any particular JSON dialect in SQL.
        """
        cur = self._conn.execute(
            """
            SELECT tags_json
            FROM cards
            WHERE deck_id = ?
            ORDER BY created_at DESC
            {limit_clause}
            """.format(
                limit_clause="LIMIT ?" if isinstance(limit, int) and limit > 0 else ""
            ),
            (deck_id,) if not (isinstance(limit, int) and limit > 0) else (deck_id, int(limit)),
        )
        labels: set[str] = set()
        for row in cur.fetchall():
            raw = row["tags_json"]
            if not raw:
                continue
            try:
                import json  # local import to avoid cost when unused

                tags = json.loads(raw)
            except Exception:
                continue
            if not isinstance(tags, list):
                continue
            for t in tags:
                if isinstance(t, str) and t.startswith("label:") and len(t) <= 128:
                    labels.add(t)
        return sorted(labels)

