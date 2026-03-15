"""Shared helpers for sessions and metrics (streak, counts, active user)."""

import uuid
from datetime import timedelta

from ..repositories.users import UserRepository

answer_requests_received: list[int] = [0]
process_token: str = uuid.uuid4().hex[:12]


def active_user_id(conn) -> str:
    """User who has submitted the most answers (for metrics)."""
    row = conn.execute(
        """
        SELECT user_id FROM events
        WHERE event_type = 'answer_submitted'
        GROUP BY user_id
        ORDER BY COUNT(*) DESC
        LIMIT 1;
        """,
    ).fetchone()
    if row:
        return str(row["user_id"])
    return UserRepository(conn).ensure_single_user()


def count_reviews_done_today(conn, user_id: str, start_iso: str, end_iso: str) -> int:
    """Number of answer_submitted events for user in [start_iso, end_iso)."""
    row = conn.execute(
        """
        SELECT COUNT(*) AS n FROM events
        WHERE user_id = ? AND event_type = 'answer_submitted' AND ts >= ? AND ts < ?;
        """,
        (user_id, start_iso, end_iso),
    ).fetchone()
    return int(row["n"]) if row else 0


def streak_days(conn, user_id: str, today_iso_date: str) -> int:
    """Consecutive days (UTC) with at least one answer, ending today. 0 if today has none."""
    from datetime import datetime

    rows = conn.execute(
        """
        SELECT DISTINCT date(ts) AS d FROM events
        WHERE user_id = ? AND event_type = 'answer_submitted'
        ORDER BY d DESC;
        """,
        (user_id,),
    ).fetchall()
    if not rows:
        return 0
    dates_with_answers = {str(r["d"]) for r in rows}
    if today_iso_date not in dates_with_answers:
        return 0
    streak = 1
    d = datetime.strptime(today_iso_date, "%Y-%m-%d").date()
    while True:
        d = d - timedelta(days=1)
        prev = d.isoformat()
        if prev not in dates_with_answers:
            break
        streak += 1
    return streak
