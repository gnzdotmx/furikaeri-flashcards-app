from datetime import timedelta

import pytest

from app.scheduler.clock import utcnow
from app.scheduler.fsrs import FsrsScheduler, _interval_scale_for_retention
from app.scheduler.strategy import ScheduleInput


def test_fsrs_scheduler_moves_due_forward_on_good():
    now = utcnow()
    # No learning steps: new card rated "good" graduates and gets a full interval.
    sched = FsrsScheduler(learning_steps_minutes=())
    inp = ScheduleInput(
        now=now,
        is_new=True,
        stability=0.0,
        difficulty=0.0,
        lapses=0,
        reps=0,
        avg_time_ms=0,
        streak=0,
    )
    out = sched.schedule(inp=inp, rating="good", time_ms=1500)
    assert out.reps == 1
    assert out.lapses == 0
    assert out.due_at > now + timedelta(hours=1)
    assert getattr(out, "learning_step", -1) == -1


def test_fsrs_scheduler_again_sets_short_due():
    now = utcnow()
    sched = FsrsScheduler()
    inp = ScheduleInput(
        now=now,
        is_new=False,
        stability=2.0,
        difficulty=5.0,
        lapses=0,
        reps=3,
        avg_time_ms=2000,
        streak=2,
    )
    out = sched.schedule(inp=inp, rating="again", time_ms=3000)
    assert out.lapses == 1
    assert out.due_at <= now + timedelta(minutes=15)


def test_fsrs_scheduler_learning_steps_new_card_good():
    """With learning steps, new card rated good goes to step 1 and is due in second step minutes."""
    from app.scheduler.fsrs import DEFAULT_LEARNING_STEPS_MINUTES

    now = utcnow()
    sched = FsrsScheduler(learning_steps_minutes=DEFAULT_LEARNING_STEPS_MINUTES)
    inp = ScheduleInput(
        now=now,
        is_new=True,
        stability=0.0,
        difficulty=0.0,
        lapses=0,
        reps=0,
        avg_time_ms=0,
        streak=0,
    )
    out = sched.schedule(inp=inp, rating="good", time_ms=1000)
    assert out.learning_step == 1
    assert out.due_at <= now + timedelta(minutes=15)
    assert out.due_at >= now + timedelta(seconds=30)


def test_fsrs_scheduler_learning_steps_again_resets_to_step_zero():
    """Again during learning resets to step 0 (due in first step minutes)."""
    from app.scheduler.fsrs import DEFAULT_LEARNING_STEPS_MINUTES

    now = utcnow()
    sched = FsrsScheduler(learning_steps_minutes=DEFAULT_LEARNING_STEPS_MINUTES)
    inp = ScheduleInput(
        now=now,
        is_new=False,
        stability=0.6,
        difficulty=5.0,
        lapses=0,
        reps=1,
        avg_time_ms=1000,
        streak=0,
        learning_step=1,
    )
    out = sched.schedule(inp=inp, rating="again", time_ms=500)
    assert out.learning_step == 0
    assert out.due_at <= now + timedelta(minutes=5)
    assert out.lapses == 0  # learning again does not count as lapse


def test_interval_scale_baseline():
    """At default target retention 0.9, scale is 1.0."""
    assert _interval_scale_for_retention(0.9) == pytest.approx(1.0)


def test_target_retention_higher_shorter_interval():
    """Higher target retention (e.g. 95%) shortens intervals."""
    now = utcnow()
    # Graduated card, stability=2.0, rate "good" -> baseline interval = 2.0 days
    inp = ScheduleInput(
        now=now,
        is_new=False,
        stability=2.0,
        difficulty=5.0,
        lapses=0,
        reps=2,
        avg_time_ms=1000,
        streak=1,
    )
    sched_default = FsrsScheduler(learning_steps_minutes=(), target_retention=0.9)
    sched_high = FsrsScheduler(learning_steps_minutes=(), target_retention=0.95)
    out_default = sched_default.schedule(inp=inp, rating="good", time_ms=1000)
    out_high = sched_high.schedule(inp=inp, rating="good", time_ms=1000)
    # 0.95 -> scale < 1, so interval shorter
    assert (out_high.due_at - now).total_seconds() < (out_default.due_at - now).total_seconds()


def test_target_retention_lower_longer_interval():
    """Lower target retention (e.g. 85%) lengthens intervals."""
    now = utcnow()
    inp = ScheduleInput(
        now=now,
        is_new=False,
        stability=2.0,
        difficulty=5.0,
        lapses=0,
        reps=2,
        avg_time_ms=1000,
        streak=1,
    )
    sched_default = FsrsScheduler(learning_steps_minutes=(), target_retention=0.9)
    sched_low = FsrsScheduler(learning_steps_minutes=(), target_retention=0.85)
    out_default = sched_default.schedule(inp=inp, rating="good", time_ms=1000)
    out_low = sched_low.schedule(inp=inp, rating="good", time_ms=1000)
    # 0.85 -> scale > 1, so interval longer
    assert (out_low.due_at - now).total_seconds() > (out_default.due_at - now).total_seconds()
