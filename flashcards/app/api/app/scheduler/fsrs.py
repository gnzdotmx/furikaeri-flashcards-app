from __future__ import annotations

import math
from datetime import datetime, timedelta

from app.study_config import get_study_config
from .strategy import ScheduleInput, ScheduleOutput, Scheduler


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


# Baseline retention the scheduler is tuned for; interval_scale = 1.0 at this target.
DEFAULT_TARGET_RETENTION = 0.9


def _interval_scale_for_retention(target_retention: float) -> float:
    """Scale factor: higher retention → shorter intervals. scale = ln(R)/ln(0.9)."""
    r = _clamp(float(target_retention), 0.5, 0.99)
    return math.log(r) / math.log(DEFAULT_TARGET_RETENTION)


def _default_learning_steps_minutes() -> tuple[int, ...]:
    return get_study_config().scheduler.learning_steps_minutes


# Default learning steps in minutes (from config); use when no user override.
DEFAULT_LEARNING_STEPS_MINUTES: tuple[int, ...] = (1, 10)  # fallback if config not loaded yet


class FsrsScheduler(Scheduler):
    """FSRS-style: stability, difficulty, learning_step (-1=graduated). New cards do learning steps then intervals."""

    def __init__(
        self,
        *,
        stability_multiplier: float = 1.0,
        target_retention: float | None = None,
        learning_steps_minutes: tuple[int, ...] | None = None,
    ):
        cfg = get_study_config().scheduler
        self.stability_multiplier = float(stability_multiplier)
        self.target_retention = _clamp(
            float(target_retention if target_retention is not None else cfg.target_retention), 0.5, 0.99
        )
        self._interval_scale = _interval_scale_for_retention(self.target_retention)
        # Explicit empty tuple = no learning steps; None = use config.
        if learning_steps_minutes is not None:
            self.learning_steps_minutes = tuple(learning_steps_minutes)
        else:
            self.learning_steps_minutes = cfg.learning_steps_minutes
        self._leech_threshold = cfg.leech_lapses_threshold
        self._response_time_cap_ms = cfg.response_time_cap_minutes * 60 * 1000
        self._again_minutes = cfg.again_review_minutes
        self._stability_min = cfg.stability_min
        self._stability_max = cfg.stability_max
        self._interval_min_hard = cfg.interval_min_hard_days
        self._interval_min_good = cfg.interval_min_good_days
        self._interval_min_easy = cfg.interval_min_easy_days

    def schedule(self, *, inp: ScheduleInput, rating: str, time_ms: int) -> ScheduleOutput:
        if rating not in ("again", "hard", "good", "easy"):
            raise ValueError("rating must be again|hard|good|easy")

        reps = inp.reps + 1
        lapses = inp.lapses
        streak = inp.streak

        # Rolling avg response time (avoid storing raw answers)
        time_ms = max(0, min(int(time_ms), self._response_time_cap_ms))
        avg_time = int(inp.avg_time_ms * 0.8 + time_ms * 0.2) if inp.avg_time_ms else time_ms

        # In learning: first time (new) or current step < num_steps.
        in_learning = inp.is_new or (
            self.learning_steps_minutes and inp.learning_step >= 0 and inp.learning_step < len(self.learning_steps_minutes)
        )

        if in_learning and self.learning_steps_minutes:
            # Learning steps: again -> step 0; hard/good/easy -> advance or graduate.
            if rating == "again":
                next_step = 0
                due = inp.now + timedelta(minutes=self.learning_steps_minutes[0])
                # Don't bump lapses for learning "again" to avoid inflating leech detection.
                lapses = inp.lapses
                streak = 0
                stability = inp.stability if not inp.is_new else 0.6
                difficulty = inp.difficulty if not inp.is_new else 5.0
            else:
                current_step = 0 if inp.is_new else inp.learning_step
                next_step = current_step + 1
                stability = 0.6 if inp.is_new else inp.stability
                difficulty = 5.0 if inp.is_new else inp.difficulty
                if next_step >= len(self.learning_steps_minutes):
                    # Graduate: run normal interval logic and set learning_step = -1.
                    due, stability, difficulty, lapses, streak = self._interval_for_rating(
                        inp.now, rating, stability, difficulty, lapses, streak
                    )
                    next_step = -1
                else:
                    due = inp.now + timedelta(minutes=self.learning_steps_minutes[next_step])
                    streak = max(0, streak) + 1

            leech_flag = 1 if lapses >= self._leech_threshold else 0
            return ScheduleOutput(
                due_at=due,
                stability=float(stability),
                difficulty=float(difficulty),
                lapses=int(lapses),
                reps=int(reps),
                avg_time_ms=int(avg_time),
                streak=int(streak),
                leech_flag=int(leech_flag),
                learning_step=int(next_step),
            )

        # Graduated (or no learning steps): normal FSRS.
        stability = inp.stability if not inp.is_new else 0.6
        difficulty = inp.difficulty if not inp.is_new else 5.0
        due, stability, difficulty, lapses, streak = self._interval_for_rating(
            inp.now, rating, stability, difficulty, lapses, streak
        )
        leech_flag = 1 if lapses >= self._leech_threshold else 0
        return ScheduleOutput(
            due_at=due,
            stability=float(stability),
            difficulty=float(difficulty),
            lapses=int(lapses),
            reps=int(reps),
            avg_time_ms=int(avg_time),
            streak=int(streak),
            leech_flag=int(leech_flag),
            learning_step=-1,
        )

    def _interval_for_rating(
        self,
        now: datetime,
        rating: str,
        stability: float,
        difficulty: float,
        lapses: int,
        streak: int,
    ) -> tuple[datetime, float, float, int, int]:
        if rating == "again":
            lapses += 1
            streak = 0
            difficulty = _clamp(difficulty + 0.9, 1.0, 10.0)
            stability = _clamp(
                stability * 0.55 * self.stability_multiplier, self._stability_min, self._stability_max
            )
            due = now + timedelta(minutes=self._again_minutes)
        elif rating == "hard":
            streak = max(0, streak) + 1
            difficulty = _clamp(difficulty + 0.2, 1.0, 10.0)
            stability = _clamp(
                stability * 1.25 * self.stability_multiplier, self._stability_min, self._stability_max
            )
            interval_days = max(self._interval_min_hard, stability * 0.8 * self._interval_scale)
            due = now + timedelta(days=interval_days)
        elif rating == "good":
            streak = max(0, streak) + 1
            difficulty = _clamp(difficulty - 0.15, 1.0, 10.0)
            stability = _clamp(
                stability * 1.7 * self.stability_multiplier, self._stability_min, self._stability_max
            )
            interval_days = max(self._interval_min_good, stability * self._interval_scale)
            due = now + timedelta(days=interval_days)
        else:  # easy
            streak = max(0, streak) + 1
            difficulty = _clamp(difficulty - 0.35, 1.0, 10.0)
            stability = _clamp(
                stability * 2.2 * self.stability_multiplier, self._stability_min, self._stability_max
            )
            interval_days = max(self._interval_min_easy, stability * 1.3 * self._interval_scale)
            due = now + timedelta(days=interval_days)
        return (due, stability, difficulty, lapses, streak)

