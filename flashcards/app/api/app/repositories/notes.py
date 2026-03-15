import uuid

from .base import BaseRepository


class NoteRepository(BaseRepository):
    def upsert_note(
        self,
        *,
        source_type: str,
        level: str,
        key: str,
        fields_json: str,
        source_url: str | None = None,
        note_id: str | None = None,
    ) -> str:
        """Upsert note by (source_type, level, key)."""
        nid = note_id or str(uuid.uuid4())
        self._conn.execute(
            """
            INSERT INTO notes(id, source_type, level, key, fields_json, source_url, created_at)
            VALUES(?, ?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            ON CONFLICT(source_type, level, key) DO UPDATE SET
              fields_json=excluded.fields_json,
              source_url=excluded.source_url;
            """,
            (nid, source_type, level, key, fields_json, source_url),
        )
        row = self._conn.execute(
            "SELECT id FROM notes WHERE source_type = ? AND level = ? AND key = ?;",
            (source_type, level, key),
        ).fetchone()
        return str(row["id"]) if row else nid

    def get_note(self, note_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT id, source_type, level, key, fields_json, source_url, created_at FROM notes WHERE id = ?;",
            (note_id,),
        ).fetchone()
        return dict(row) if row else None

    def get_note_by_key(self, *, source_type: str, level: str, key: str) -> dict | None:
        row = self._conn.execute(
            "SELECT id, source_type, level, key, fields_json, source_url, created_at FROM notes WHERE source_type = ? AND level = ? AND key = ?;",
            (source_type, level, key),
        ).fetchone()
        return dict(row) if row else None

    def list_notes(self, *, source_type: str | None = None, level: str | None = None, limit: int = 200) -> list[dict]:
        where = []
        params: list[object] = []
        if source_type:
            where.append("source_type = ?")
            params.append(source_type)
        if level:
            where.append("level = ?")
            params.append(level)
        sql = "SELECT id, source_type, level, key, source_url, created_at FROM notes"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY created_at DESC LIMIT ?;"
        params.append(int(limit))
        rows = self._conn.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]

