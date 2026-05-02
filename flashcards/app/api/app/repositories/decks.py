import uuid

from .base import BaseRepository


class DeckRepository(BaseRepository):
    def get_deck_by_name(self, name: str) -> dict | None:
        row = self._conn.execute(
            "SELECT id, name, description, created_at, updated_at FROM decks WHERE name = ? ORDER BY created_at ASC LIMIT 1;",
            (name,),
        ).fetchone()
        return dict(row) if row else None

    def create_deck(self, name: str, description: str | None = None, deck_id: str | None = None) -> str:
        existing = self.get_deck_by_name(name)
        if existing:
            return str(existing["id"])
        did = deck_id or str(uuid.uuid4())
        self._conn.execute(
            """
            INSERT INTO decks(id, name, description, created_at, updated_at)
            VALUES(?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'), strftime('%Y-%m-%dT%H:%M:%fZ','now'));
            """,
            (did, name, description),
        )
        return did

    def list_decks(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, name, description, created_at, updated_at FROM decks ORDER BY created_at DESC;"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_deck(self, deck_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT id, name, description, created_at, updated_at FROM decks WHERE id = ?;",
            (deck_id,),
        ).fetchone()
        return dict(row) if row else None

    def delete_deck(self, deck_id: str) -> bool:
        cur = self._conn.execute("DELETE FROM decks WHERE id = ?;", (deck_id,))
        return int(cur.rowcount or 0) > 0

