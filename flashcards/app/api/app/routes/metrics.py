"""Metrics, client events, user settings."""

import json
import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..auth import get_current_user_id
from ..db import connection, transaction
from ..repositories.events import EventRepository
from ..repositories.users import UserRepository
from ..scheduler.clock import isoformat_z, utcnow
from ..settings import Settings, get_settings
from ..study_config import get_study_config
from .common import count_reviews_done_today, streak_days
from .dependencies import get_sqlite_path

logger = logging.getLogger(__name__)
router = APIRouter()


class ClientEventReq(BaseModel):
    session_id: str | None = Field(default=None, max_length=80)
    card_id: str | None = Field(default=None, max_length=80)
    event_type: str = Field(..., max_length=64)
    payload: dict = Field(default_factory=dict)


@router.post("/events")
def append_event(
    req: ClientEventReq,
    user_id: str = Depends(get_current_user_id),
    settings: Settings = Depends(get_settings),
):
    """Store client events (hint, audio, reveal). No typed/raw answers."""
    allowed = {"hint_toggled", "audio_played", "reveal_toggled"}
    if req.event_type not in allowed:
        raise HTTPException(status_code=400, detail="unsupported event_type")

    payload = dict(req.payload or {})
    for k in ["typed_answer", "raw_answer", "text"]:
        payload.pop(k, None)
    payload["v"] = 1
    if req.card_id:
        payload["card_id"] = req.card_id

    with connection(settings.sqlite_path) as conn:
        with transaction(conn):
            EventRepository(conn).append_event(
                user_id=user_id,
                session_id=req.session_id,
                event_type=req.event_type,
                payload_json=json.dumps(payload, separators=(",", ":")),
            )
    return {"ok": True}


class UserSettingsUpdateReq(BaseModel):
    daily_goal_reviews: int | None = Field(
        default=None,
        ge=0,
        description="Optional daily review goal; 0 or omit to clear. Max from study_config.session.daily_goal_reviews_max.",
    )


@router.get("/users/settings")
def get_user_settings(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    sqlite_path: str = Depends(get_sqlite_path),
):
    """Scheduling and goal settings for current user."""
    with connection(sqlite_path) as conn:
        settings = UserRepository(conn).get_settings(user_id) or {}
    daily_goal = settings.get("daily_goal_reviews")
    if daily_goal is not None and isinstance(daily_goal, int) and daily_goal <= 0:
        daily_goal = None
    cfg = get_study_config()
    return {
        "new_cards_per_day": settings.get("new_cards_per_day", cfg.session.new_cards_per_day_default),
        "target_retention": settings.get("target_retention", cfg.scheduler.target_retention),
        "daily_goal_reviews": daily_goal,
    }


@router.patch("/users/settings")
def update_user_settings(
    request: Request,
    req: UserSettingsUpdateReq,
    user_id: str = Depends(get_current_user_id),
    sqlite_path: str = Depends(get_sqlite_path),
):
    """Update user settings (e.g. daily goal)."""
    with connection(sqlite_path) as conn:
        with transaction(conn):
            if req.daily_goal_reviews is not None:
                max_goal = get_study_config().session.daily_goal_reviews_max
                value = min(max(req.daily_goal_reviews, 0), max_goal)
                UserRepository(conn).update_settings(user_id, daily_goal_reviews=(value if value > 0 else None))
        settings = UserRepository(conn).get_settings(user_id) or {}
    daily_goal = settings.get("daily_goal_reviews")
    if daily_goal is not None and isinstance(daily_goal, int) and daily_goal <= 0:
        daily_goal = None
    return {
        "daily_goal_reviews": daily_goal,
    }


@router.get("/metrics/summary")
def metrics_summary(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    sqlite_path: str = Depends(get_sqlite_path),
    limit: int | None = None,
):
    """Metrics summary (same DB as request)."""
    lim_cfg = get_study_config().limits
    limit = int(limit) if limit is not None else lim_cfg.metrics_summary_default
    limit = max(lim_cfg.metrics_summary_min, min(limit, lim_cfg.metrics_summary_max))
    with connection(sqlite_path) as conn:
        rows = conn.execute(
            """
            SELECT payload_json
            FROM events
            WHERE user_id = ? AND event_type = 'answer_submitted'
            ORDER BY ts DESC
            LIMIT ?;
            """,
            (user_id, limit),
        ).fetchall()
        n = len(rows)
        by_rating = {"again": 0, "hard": 0, "good": 0, "easy": 0}
        times = []
        again_n = 0
        for r in rows:
            try:
                payload = json.loads(r["payload_json"])
                rating = payload.get("rating") or "unknown"
                if rating in by_rating:
                    by_rating[rating] += 1
                if rating == "again":
                    again_n += 1
                times.append(int(payload.get("time_ms") or 0))
            except Exception:
                logger.debug(
                    "Skipping malformed metrics payload",
                    extra={"user_id": user_id},
                )
        avg_time_ms = int(sum(times) / len(times)) if times else 0
        again_rate = (again_n / n) if n else 0.0
        retention_proxy = 1.0 - again_rate

        now = utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        user_settings = UserRepository(conn).get_settings(user_id) or {}
        daily_goal = user_settings.get("daily_goal_reviews")
        if daily_goal is not None and isinstance(daily_goal, int) and daily_goal <= 0:
            daily_goal = None
        reviews_done_today = count_reviews_done_today(conn, user_id, isoformat_z(today_start), isoformat_z(today_end))
        streak = streak_days(conn, user_id, today_start.date().isoformat())

        return {
            "n": n,
            "by_rating": by_rating,
            "again_rate": round(again_rate, 3),
            "retention_proxy": round(retention_proxy, 3),
            "avg_time_ms": avg_time_ms,
            "daily_goal_reviews": daily_goal,
            "reviews_done_today": reviews_done_today,
            "streak_days": streak,
        }


