import uuid

from .base import BaseRepository


class EventRepository(BaseRepository):
    def append_event(
        self,
        *,
        user_id: str,
        event_type: str,
        payload_json: str,
        ts: str | None = None,
        session_id: str | None = None,
        event_id: str | None = None,
    ) -> str:
        eid = event_id or str(uuid.uuid4())
        # Use provided ts if present; otherwise use server time.
        if ts:
            self._conn.execute(
                """
                INSERT INTO events(event_id, ts, user_id, session_id, event_type, payload_json, created_at)
                VALUES(?, ?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'));
                """,
                (eid, ts, user_id, session_id, event_type, payload_json),
            )
        else:
            self._conn.execute(
                """
                INSERT INTO events(event_id, ts, user_id, session_id, event_type, payload_json, created_at)
                VALUES(?, strftime('%Y-%m-%dT%H:%M:%fZ','now'), ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'));
                """,
                (eid, user_id, session_id, event_type, payload_json),
            )
        return eid

