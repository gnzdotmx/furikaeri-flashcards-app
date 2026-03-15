"""Session logic: start session, next card, submit answer. Routes do HTTP and ownership checks."""

import json
import logging
import random

from ..db import transaction
from ..repositories.cards import CardRepository
from ..repositories.events import EventRepository
from ..repositories.reviews import ReviewRepository
from ..repositories.sessions import SessionRepository
from ..repositories.users import UserRepository
from ..scheduler.clock import isoformat_z, utcnow
from ..scheduler.fsrs import FsrsScheduler, _default_learning_steps_minutes
from ..scheduler.strategy import ScheduleInput
from ..study_config import get_study_config
from ..personalization.bandit import reward_from_outcome
from ..personalization.repository import BanditRepository, FsrsParamsRepository
from ..cards.types import CardType

logger = logging.getLogger(__name__)


def start_session(
    conn,
    user_id: str,
    deck_id: str,
    mode: str,
    new_limit: int,
    include_listening: bool,
) -> str:
    """Create study session. Returns session_id."""
    with transaction(conn):
        sid = SessionRepository(conn).create_session(
            user_id=user_id,
            deck_id=deck_id,
            mode=mode,
            new_limit=new_limit,
            include_listening=include_listening,
        )
    return sid


def get_next_card(conn, session_id: str, sess: dict, label: str | None) -> dict:
    """Pick next card or return done. Returns {kind: "done"} or {kind, card, new_remaining, presentation_defaults}."""
    sessions = SessionRepository(conn)
    user_id = sess["user_id"]
    deck_id = sess["deck_id"]
    new_remaining = max(0, int(sess["new_limit"]) - int(sess["new_shown"]))
    include_listening = bool(sess.get("include_listening", 1))
    cards = CardRepository(conn)
    exclude_listening = () if include_listening else (CardType.VOCAB_LISTENING,)
    now = utcnow()
    now_iso = isoformat_z(now)
    sess_cfg = get_study_config().session
    _BACKLOG_THRESHOLD = sess_cfg.backlog_threshold
    _BACKLOG_VERY_HIGH = sess_cfg.backlog_very_high
    _BACKLOG_OVERWHELMING = sess_cfg.backlog_overwhelming
    furigana_mode = "hover"
    num_learning_steps = len(_default_learning_steps_minutes())
    learning_candidates = (
        cards.get_next_learning_cards(
            deck_id=deck_id,
            user_id=user_id,
            now_iso=now_iso,
            num_steps=num_learning_steps,
            limit=sess_cfg.candidate_limit,
            exclude_card_types=exclude_listening,
            label_tag=label,
        )
        if num_learning_steps else []
    )
    due_now = cards.count_due_now(deck_id=deck_id, user_id=user_id, now_iso=now_iso)
    due_first_order = ["again", "learning", "hard", "good", "new"]
    r = random.random()
    if due_now >= _BACKLOG_OVERWHELMING:
        pool_order = due_first_order
    elif due_now >= _BACKLOG_VERY_HIGH:
        pool_order = due_first_order if r < sess_cfg.pool_due_first_prob_very_high else ["new", "again", "learning", "hard", "good"]
    elif due_now >= _BACKLOG_THRESHOLD:
        pool_order = due_first_order if r < sess_cfg.pool_due_first_prob_high else ["new", "again", "learning", "hard", "good"]
    else:
        if r < sess_cfg.pool_again_prob:
            pool_order = ["again", "learning", "new", "hard", "good"]
        elif r < sess_cfg.pool_again_prob + sess_cfg.pool_learning_prob:
            pool_order = ["learning", "new", "again", "hard", "good"]
        elif r < sess_cfg.pool_again_prob + sess_cfg.pool_learning_prob + sess_cfg.pool_hard_prob:
            pool_order = ["hard", "again", "learning", "new", "good"]
        else:
            pool_order = ["good", "again", "learning", "new", "hard"]

    chosen = None
    kind = None
    for pool in pool_order:
        candidates = []
        if pool == "learning" and learning_candidates:
            candidates = learning_candidates
            kind = "learning"
        elif pool == "again":
            candidates = cards.get_next_due_cards(
                deck_id=deck_id,
                user_id=user_id,
                now_iso=now_iso,
                session_id=session_id,
                limit=sess_cfg.candidate_limit,
                exclude_card_types=exclude_listening,
                label_tag=label,
            )
            kind = "due"
        elif pool == "new" and new_remaining > 0:
            candidates = cards.get_next_new_cards(
                deck_id=deck_id,
                user_id=user_id,
                session_id=session_id,
                limit=sess_cfg.candidate_limit,
                exclude_card_types=exclude_listening,
                label_tag=label,
            )
            kind = "new"
        elif pool == "hard":
            candidates = cards.get_next_due_cards_with_last_rating(
                deck_id=deck_id,
                user_id=user_id,
                now_iso=now_iso,
                session_id=session_id,
                last_ratings=("hard",),
                limit=sess_cfg.candidate_limit,
                exclude_card_types=exclude_listening,
                label_tag=label,
            )
            kind = "due"
        elif pool == "good":
            candidates = cards.get_next_due_cards_with_last_rating(
                deck_id=deck_id,
                user_id=user_id,
                now_iso=now_iso,
                session_id=session_id,
                last_ratings=("good", "easy"),
                limit=sess_cfg.candidate_limit,
                exclude_card_types=exclude_listening,
                label_tag=label,
            )
            kind = "due"
        if candidates:
            chosen = random.choice(candidates)
            break

    if chosen:
        with transaction(conn):
            if kind != "learning":
                sessions.mark_seen(session_id=session_id, card_id=chosen["id"])
            if kind == "new":
                sessions.increment_new_shown(session_id=session_id)
            EventRepository(conn).append_event(
                user_id=user_id,
                session_id=session_id,
                event_type="card_shown",
                payload_json=json.dumps(
                    {"v": 1, "card_id": chosen["id"], "kind": kind, "furigana_mode": furigana_mode},
                    separators=(",", ":"),
                ),
            )
        if kind == "new":
            sess2 = sessions.get_session(session_id) or sess
            new_remaining = max(0, int(sess2["new_limit"]) - int(sess2["new_shown"]))
        return {"kind": kind, "card": chosen, "new_remaining": new_remaining, "presentation_defaults": {"furigana_mode": furigana_mode}}

    with transaction(conn):
        sessions.end_session(session_id=session_id)
    return {"kind": "done"}


def process_answer(conn, sess: dict, session_id: str, card_id: str, rating: str, time_ms: int, hints_used: int) -> dict:
    """Record answer, update review state and FSRS, maybe bandit. Returns response dict for POST answer."""
    import os

    from ..routes.common import process_token

    user_id = sess["user_id"]
    reviews = ReviewRepository(conn)
    rs = reviews.get_review_state(card_id, user_id)
    is_new = rs is None
    learning_step = int(rs.get("learning_step", -1)) if rs else -1
    if learning_step is None or learning_step < 0:
        learning_step = -1

    fsrs_params = FsrsParamsRepository(conn).get_params(user_id)
    user_settings = UserRepository(conn).get_settings(user_id) or {}
    sched_cfg = get_study_config().scheduler
    target_retention = float(user_settings.get("target_retention", sched_cfg.target_retention))
    raw_steps = fsrs_params.get("learning_steps_minutes")
    if isinstance(raw_steps, (list, tuple)) and len(raw_steps) > 0:
        learning_steps_minutes = tuple(int(x) for x in raw_steps)
    else:
        learning_steps_minutes = sched_cfg.learning_steps_minutes
    scheduler = FsrsScheduler(
        stability_multiplier=float(fsrs_params.get("stability_multiplier", 1.0)),
        target_retention=target_retention,
        learning_steps_minutes=learning_steps_minutes,
    )

    inp = ScheduleInput(
        now=utcnow(),
        is_new=is_new,
        stability=float(rs["stability"]) if rs else 0.0,
        difficulty=float(rs["difficulty"]) if rs else 0.0,
        lapses=int(rs["lapses"]) if rs else 0,
        reps=int(rs["reps"]) if rs else 0,
        avg_time_ms=int(rs["avg_time_ms"]) if rs else 0,
        streak=int(rs["streak"]) if rs else 0,
        learning_step=0 if is_new else learning_step,
    )

    out = scheduler.schedule(inp=inp, rating=rating, time_ms=time_ms)

    with transaction(conn):
        reviews.upsert_review_state(
            card_id=card_id,
            user_id=user_id,
            due_at=isoformat_z(out.due_at),
            stability=out.stability,
            difficulty=out.difficulty,
            last_rating=rating,
            lapses=out.lapses,
            reps=out.reps,
            avg_time_ms=out.avg_time_ms,
            streak=out.streak,
            leech_flag=out.leech_flag,
            learning_step=getattr(out, "learning_step", -1),
        )
        EventRepository(conn).append_event(
            user_id=user_id,
            session_id=session_id,
            event_type="answer_submitted",
            payload_json=json.dumps(
                {"v": 1, "card_id": card_id, "rating": rating, "time_ms": time_ms, "hints_used": hints_used, "is_new": is_new},
                separators=(",", ":"),
            ),
        )
    conn.commit()

    answer_total_row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM events WHERE user_id = ? AND event_type = 'answer_submitted';",
        (user_id,),
    ).fetchone()
    answer_submitted_total = int(answer_total_row["cnt"]) if answer_total_row else 0

    try:
        with transaction(conn):
            row = conn.execute(
                """
                SELECT payload_json
                FROM events
                WHERE user_id = ? AND session_id = ? AND event_type = 'card_shown'
                ORDER BY ts DESC
                LIMIT 50;
                """,
                (user_id, session_id),
            ).fetchall()
            arm = None
            if row:
                for rr in row:
                    try:
                        payload = json.loads(rr["payload_json"])
                        if payload.get("card_id") == card_id:
                            arm = payload.get("furigana_mode")
                            break
                    except (json.JSONDecodeError, TypeError):
                        logger.debug(
                            "Skipping malformed card_shown payload",
                            extra={"session_id": session_id},
                        )
                        continue
            if arm in ("off", "hover", "on"):
                BanditRepository(conn).update_arm(
                    user_id=user_id,
                    experiment_key="furigana_mode",
                    arm_key=arm,
                    reward=reward_from_outcome(rating=rating, time_ms=time_ms),
                )

            last = conn.execute(
                """
                SELECT payload_json
                FROM events
                WHERE user_id = ? AND event_type = 'answer_submitted'
                ORDER BY ts DESC
                LIMIT 200;
                """,
                (user_id,),
            ).fetchall()
            if last and len(last) >= 30:
                n = 0
                again_n = 0
                for rr in last:
                    try:
                        payload = json.loads(rr["payload_json"])
                        if payload.get("rating") == "again":
                            again_n += 1
                        n += 1
                    except (json.JSONDecodeError, TypeError):
                        logger.debug(
                            "Skipping malformed answer_submitted payload",
                            extra={"session_id": session_id},
                        )
                        continue
                again_rate = float(again_n) / float(max(1, n))
                user_settings = UserRepository(conn).get_settings(user_id) or {}
                target = float(user_settings.get("target_retention", get_study_config().scheduler.target_retention))
                mult = float(FsrsParamsRepository(conn).get_params(user_id).get("stability_multiplier", 1.0))
                if again_rate > (1.0 - target) + 0.05:
                    mult = max(0.7, mult - 0.02)
                elif again_rate < (1.0 - target) - 0.05:
                    mult = min(1.3, mult + 0.01)
                FsrsParamsRepository(conn).set_stability_multiplier(user_id, mult)
    except Exception as e:
        logger.warning(
            "Bandit/FSRS update failed (answer still saved): %s",
            type(e).__name__,
            extra={"session_id": session_id, "user_id": user_id, "card_id": card_id},
        )

    return {
        "ok": True,
        "card_id": card_id,
        "rating": rating,
        "is_new": is_new,
        "next_due_at": isoformat_z(out.due_at),
        "stability": out.stability,
        "difficulty": out.difficulty,
        "lapses": out.lapses,
        "reps": out.reps,
        "leech_flag": out.leech_flag,
        "answer_submitted_total": answer_submitted_total,
        "_pid": os.getpid(),
        "_process_token": process_token,
    }
