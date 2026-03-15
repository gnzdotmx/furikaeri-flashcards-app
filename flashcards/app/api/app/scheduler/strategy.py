from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


Rating = str  # again|hard|good|easy


@dataclass(frozen=True)
class ScheduleInput:
    now: datetime
    is_new: bool
    stability: float
    difficulty: float
    lapses: int
    reps: int
    avg_time_ms: int
    streak: int
    # Learning step index: -1 = graduated, 0..n-1 = in learning (current step).
    learning_step: int = -1


@dataclass(frozen=True)
class ScheduleOutput:
    due_at: datetime
    stability: float
    difficulty: float
    lapses: int
    reps: int
    avg_time_ms: int
    streak: int
    leech_flag: int
    # -1 = graduated, 0..n-1 = next step to show.
    learning_step: int = -1


class Scheduler:
    def schedule(self, *, inp: ScheduleInput, rating: Rating, time_ms: int) -> ScheduleOutput:
        raise NotImplementedError

