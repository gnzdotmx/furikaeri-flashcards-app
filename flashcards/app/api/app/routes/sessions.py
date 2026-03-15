"""Sessions: start, next card, submit answer."""

import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..auth import get_current_user_id
from ..db import connection
from ..repositories.decks import DeckRepository
from ..repositories.sessions import SessionRepository
from ..repositories.users import UserRepository
from ..scheduler.clock import isoformat_z, utcnow
from ..study_config import get_study_config
from ..repositories.cards import CardRepository
from .common import answer_requests_received, count_reviews_done_today, streak_days
from .dependencies import get_sqlite_path
from ..services.session_service import start_session as start_session_svc, get_next_card, process_answer as process_answer_svc

logger = logging.getLogger(__name__)
router = APIRouter()


class SessionStartReq(BaseModel):
    deck_id: str = Field(..., min_length=1, max_length=80)
    mode: str = Field(default="mixed", max_length=32)
    new_cards_per_day: int | None = Field(default=None, ge=0, le=200)
    catch_up: bool = Field(default=False, description="If true, new_limit=0 for this session (clear backlog only).")
    include_listening: bool = Field(
        default=True,
        description="If false, vocab_listening cards are excluded from this session (e.g. when user can't play sounds).",
    )


@router.post("/sessions/start")
def start_session(
    request: Request,
    req: SessionStartReq,
    user_id: str = Depends(get_current_user_id),
    sqlite_path: str = Depends(get_sqlite_path),
):
    now = utcnow()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    with connection(sqlite_path) as conn:
        users = UserRepository(conn)
        user_settings = users.get_settings(user_id) or {}
        sess_cfg = get_study_config().session
        default_new = sess_cfg.new_cards_per_day_default

        deck = DeckRepository(conn).get_deck(req.deck_id)
        if not deck:
            raise HTTPException(status_code=404, detail="deck not found")

        cards = CardRepository(conn)
        due_now = cards.count_due_now(deck_id=req.deck_id, user_id=user_id, now_iso=isoformat_z(now))
        due_today = cards.count_due_today(deck_id=req.deck_id, user_id=user_id, start_iso=isoformat_z(start), end_iso=isoformat_z(end))
        new_available = cards.count_new_available(deck_id=req.deck_id, user_id=user_id)

        base_new = int(req.new_cards_per_day) if req.new_cards_per_day is not None else int(
            user_settings.get("new_cards_per_day", default_new)
        )

        if req.catch_up:
            recommended_new = 0
        elif due_now > sess_cfg.due_now_threshold_full_stop:
            recommended_new = 0
        elif due_now > sess_cfg.due_now_threshold_cap_5:
            recommended_new = min(base_new, 5)
        elif due_now > sess_cfg.due_now_threshold_cap_7:
            recommended_new = min(base_new, 7)
        elif due_now > sess_cfg.due_now_threshold_cap_10:
            recommended_new = min(base_new, 10)
        else:
            recommended_new = base_new

        leech_count = cards.count_leeches(deck_id=req.deck_id, user_id=user_id)
        if leech_count >= sess_cfg.leech_count_no_new:
            recommended_new = min(recommended_new, 0)
        elif leech_count >= sess_cfg.leech_count_cap_3:
            recommended_new = min(recommended_new, 3)

        sid = start_session_svc(
            conn, user_id=user_id, deck_id=req.deck_id, mode=req.mode,
            new_limit=recommended_new, include_listening=req.include_listening,
        )

        est_cards = due_now + min(new_available, recommended_new)
        est_minutes = round((est_cards * sess_cfg.estimated_seconds_per_review) / 60.0, 1)

        daily_goal = user_settings.get("daily_goal_reviews")
        if daily_goal is not None and isinstance(daily_goal, int) and daily_goal <= 0:
            daily_goal = None
        reviews_done_today = count_reviews_done_today(conn, user_id, isoformat_z(start), isoformat_z(end))
        streak = streak_days(conn, user_id, start.date().isoformat())

        return {
            "session_id": sid,
            "deck": {"id": deck["id"], "name": deck["name"]},
            "due_now": due_now,
            "due_today": due_today,
            "new_available": new_available,
            "new_limit": recommended_new,
            "estimated_minutes": est_minutes,
            "leech_count": leech_count,
            "daily_goal_reviews": daily_goal,
            "reviews_done_today": reviews_done_today,
            "streak_days": streak,
        }


@router.get("/sessions/{session_id}/next")
def session_next(
    request: Request,
    session_id: str,
    label: str | None = None,
    current_user_id: str = Depends(get_current_user_id),
    sqlite_path: str = Depends(get_sqlite_path),
):
    if len(session_id) > 80:
        raise HTTPException(status_code=400, detail="session_id too long")
    if label is not None:
        lbl = label.strip()
        if not lbl:
            label = None
        elif len(lbl) > 128:
            raise HTTPException(status_code=400, detail="label too long")
        else:
            label = lbl

    with connection(sqlite_path) as conn:
        sessions = SessionRepository(conn)
        sess = sessions.get_session(session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="session not found")
        if sess["user_id"] != current_user_id:
            raise HTTPException(status_code=403, detail="session does not belong to current user")

        return get_next_card(conn, session_id, sess, label)


class SessionAnswerReq(BaseModel):
    card_id: str = Field(..., min_length=1, max_length=80)
    rating: str = Field(..., pattern="^(again|hard|good|easy)$")
    time_ms: int = Field(default=0, ge=0, le=600000)
    hints_used: int = Field(default=0, ge=0, le=100)


@router.post("/sessions/{session_id}/answer")
def session_answer(
    request: Request,
    session_id: str,
    req: SessionAnswerReq,
    current_user_id: str = Depends(get_current_user_id),
    sqlite_path: str = Depends(get_sqlite_path),
):
    if len(session_id) > 80:
        raise HTTPException(status_code=400, detail="session_id too long")
    answer_requests_received[0] += 1

    with connection(sqlite_path) as conn:
        sessions = SessionRepository(conn)
        sess = sessions.get_session(session_id)
        if not sess:
            raise HTTPException(status_code=404, detail="session not found")
        if sess["user_id"] != current_user_id:
            raise HTTPException(status_code=403, detail="session does not belong to current user")

        return process_answer_svc(
            conn, sess, session_id,
            card_id=req.card_id, rating=req.rating, time_ms=req.time_ms, hints_used=req.hints_used,
        )
