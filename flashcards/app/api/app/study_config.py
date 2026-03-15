"""Study/scheduler config: module defaults + optional YAML (STUDY_CONFIG_PATH or {DATA_DIR}/study_config.yaml). Values clamped to safe ranges."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_TARGET_RETENTION = 0.9
DEFAULT_LEARNING_STEPS_MINUTES: tuple[int, ...] = (1, 10)
DEFAULT_LEECH_LAPSES_THRESHOLD = 8
DEFAULT_RESPONSE_TIME_CAP_MINUTES = 10
DEFAULT_STABILITY_MIN = 0.3
DEFAULT_STABILITY_MAX = 3650.0
DEFAULT_INTERVAL_MIN_HARD_DAYS = 0.25
DEFAULT_INTERVAL_MIN_GOOD_DAYS = 0.5
DEFAULT_INTERVAL_MIN_EASY_DAYS = 1.0
DEFAULT_AGAIN_REVIEW_MINUTES = 10  # graduated card rated Again

DEFAULT_NEW_CARDS_PER_DAY = 10
DEFAULT_ESTIMATED_SECONDS_PER_REVIEW = 25
DEFAULT_DAILY_GOAL_REVIEWS_MAX = 500
DEFAULT_SESSION_CANDIDATE_LIMIT = 30

DEFAULT_DUE_NOW_THRESHOLD_FULL_STOP = 200
DEFAULT_DUE_NOW_THRESHOLD_CAP_5 = 100
DEFAULT_DUE_NOW_THRESHOLD_CAP_7 = 50
DEFAULT_DUE_NOW_THRESHOLD_CAP_10 = 30

DEFAULT_LEECH_COUNT_NO_NEW = 10
DEFAULT_LEECH_COUNT_CAP_3 = 5

DEFAULT_BACKLOG_THRESHOLD = 30
DEFAULT_BACKLOG_VERY_HIGH = 50
DEFAULT_BACKLOG_OVERWHELMING = 100
DEFAULT_POOL_DUE_FIRST_PROB_VERY_HIGH = 0.95
DEFAULT_POOL_DUE_FIRST_PROB_HIGH = 0.90
DEFAULT_POOL_AGAIN_PROB = 0.50
DEFAULT_POOL_LEARNING_PROB = 0.20
DEFAULT_POOL_HARD_PROB = 0.20
DEFAULT_POOL_GOOD_PROB = 0.10

DEFAULT_BANDIT_EPSILON = 0.15
DEFAULT_BANDIT_MIN_PULLS_EXPLORE = 3
DEFAULT_BANDIT_REWARD_TIME_CAP_MS = 60_000

DEFAULT_LIST_CARDS_LIMIT = 200
DEFAULT_SEARCH_EXAMPLES_LIMIT = 80
DEFAULT_SEARCH_EXAMPLES_MAX = 200
DEFAULT_METRICS_SUMMARY_DEFAULT = 200
DEFAULT_METRICS_SUMMARY_MIN = 20
DEFAULT_METRICS_SUMMARY_MAX = 2000

DEFAULT_IMPORT_MAX_ROWS = 50_000
DEFAULT_IMPORT_MAX_CELL_CHARS = 20_000


def _clamp_int(value: Any, lo: int, hi: int, default: int) -> int:
    try:
        n = int(value)
        return max(lo, min(hi, n))
    except (TypeError, ValueError):
        return default


def _clamp_float(value: Any, lo: float, hi: float, default: float) -> float:
    try:
        n = float(value)
        return max(lo, min(hi, n))
    except (TypeError, ValueError):
        return default


def _parse_learning_steps(value: Any) -> tuple[int, ...]:
    if isinstance(value, (list, tuple)) and len(value) > 0:
        return tuple(max(0, int(x)) for x in value)
    return DEFAULT_LEARNING_STEPS_MINUTES


@dataclass(frozen=True)
class SchedulerConfig:
    target_retention: float = DEFAULT_TARGET_RETENTION
    learning_steps_minutes: tuple[int, ...] = DEFAULT_LEARNING_STEPS_MINUTES
    leech_lapses_threshold: int = DEFAULT_LEECH_LAPSES_THRESHOLD
    response_time_cap_minutes: int = DEFAULT_RESPONSE_TIME_CAP_MINUTES
    again_review_minutes: int = DEFAULT_AGAIN_REVIEW_MINUTES
    stability_min: float = DEFAULT_STABILITY_MIN
    stability_max: float = DEFAULT_STABILITY_MAX
    interval_min_hard_days: float = DEFAULT_INTERVAL_MIN_HARD_DAYS
    interval_min_good_days: float = DEFAULT_INTERVAL_MIN_GOOD_DAYS
    interval_min_easy_days: float = DEFAULT_INTERVAL_MIN_EASY_DAYS


@dataclass(frozen=True)
class SessionConfig:
    new_cards_per_day_default: int = DEFAULT_NEW_CARDS_PER_DAY
    estimated_seconds_per_review: int = DEFAULT_ESTIMATED_SECONDS_PER_REVIEW
    daily_goal_reviews_max: int = DEFAULT_DAILY_GOAL_REVIEWS_MAX
    candidate_limit: int = DEFAULT_SESSION_CANDIDATE_LIMIT
    due_now_threshold_full_stop: int = DEFAULT_DUE_NOW_THRESHOLD_FULL_STOP
    due_now_threshold_cap_5: int = DEFAULT_DUE_NOW_THRESHOLD_CAP_5
    due_now_threshold_cap_7: int = DEFAULT_DUE_NOW_THRESHOLD_CAP_7
    due_now_threshold_cap_10: int = DEFAULT_DUE_NOW_THRESHOLD_CAP_10
    leech_count_no_new: int = DEFAULT_LEECH_COUNT_NO_NEW
    leech_count_cap_3: int = DEFAULT_LEECH_COUNT_CAP_3
    backlog_threshold: int = DEFAULT_BACKLOG_THRESHOLD
    backlog_very_high: int = DEFAULT_BACKLOG_VERY_HIGH
    backlog_overwhelming: int = DEFAULT_BACKLOG_OVERWHELMING
    pool_due_first_prob_very_high: float = DEFAULT_POOL_DUE_FIRST_PROB_VERY_HIGH
    pool_due_first_prob_high: float = DEFAULT_POOL_DUE_FIRST_PROB_HIGH
    pool_again_prob: float = DEFAULT_POOL_AGAIN_PROB
    pool_learning_prob: float = DEFAULT_POOL_LEARNING_PROB
    pool_hard_prob: float = DEFAULT_POOL_HARD_PROB
    pool_good_prob: float = DEFAULT_POOL_GOOD_PROB
    bandit_epsilon: float = DEFAULT_BANDIT_EPSILON
    bandit_min_pulls_explore: int = DEFAULT_BANDIT_MIN_PULLS_EXPLORE
    bandit_reward_time_cap_ms: int = DEFAULT_BANDIT_REWARD_TIME_CAP_MS


@dataclass(frozen=True)
class LimitsConfig:
    list_cards_limit: int = DEFAULT_LIST_CARDS_LIMIT
    search_examples_limit: int = DEFAULT_SEARCH_EXAMPLES_LIMIT
    search_examples_max: int = DEFAULT_SEARCH_EXAMPLES_MAX
    metrics_summary_default: int = DEFAULT_METRICS_SUMMARY_DEFAULT
    metrics_summary_min: int = DEFAULT_METRICS_SUMMARY_MIN
    metrics_summary_max: int = DEFAULT_METRICS_SUMMARY_MAX


@dataclass(frozen=True)
class ImportConfig:
    max_rows_default: int = DEFAULT_IMPORT_MAX_ROWS
    max_cell_chars_default: int = DEFAULT_IMPORT_MAX_CELL_CHARS


@dataclass(frozen=True)
class StudyConfig:
    """All study-related tunables in one place."""

    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    limits: LimitsConfig = field(default_factory=LimitsConfig)
    import_: ImportConfig = field(default_factory=ImportConfig)


def _load_yaml_if_available() -> dict[str, Any] | None:
    path = os.getenv("STUDY_CONFIG_PATH")
    if path:
        p = Path(path)
    else:
        data_dir = os.getenv("DATA_DIR", "/data")
        p = Path(data_dir) / "study_config.yaml"
        if not p.is_file():
            p = Path.cwd() / "study_config.yaml"
    if not p.is_file():
        return None
    try:
        import yaml
        with open(p, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning("Failed to load study_config YAML %s: %s", p, e)
        return None


def _apply_overrides(raw: dict[str, Any] | None) -> StudyConfig:
    if not raw:
        return StudyConfig()

    def sub(key: str, default: dict) -> dict:
        return raw.get(key) if isinstance(raw.get(key), dict) else default

    sched = sub("scheduler", {})
    sess = sub("session", {})
    lim = sub("limits", {})
    imp = sub("import", {})

    scheduler = SchedulerConfig(
        target_retention=_clamp_float(sched.get("target_retention"), 0.5, 0.99, DEFAULT_TARGET_RETENTION),
        learning_steps_minutes=_parse_learning_steps(sched.get("learning_steps_minutes")),
        leech_lapses_threshold=_clamp_int(sched.get("leech_lapses_threshold"), 3, 20, DEFAULT_LEECH_LAPSES_THRESHOLD),
        response_time_cap_minutes=_clamp_int(sched.get("response_time_cap_minutes"), 1, 60, DEFAULT_RESPONSE_TIME_CAP_MINUTES),
        again_review_minutes=_clamp_int(sched.get("again_review_minutes"), 1, 60, DEFAULT_AGAIN_REVIEW_MINUTES),
        stability_min=_clamp_float(sched.get("stability_min"), 0.1, 1.0, DEFAULT_STABILITY_MIN),
        stability_max=_clamp_float(sched.get("stability_max"), 100.0, 10000.0, DEFAULT_STABILITY_MAX),
        interval_min_hard_days=_clamp_float(sched.get("interval_min_hard_days"), 0.1, 1.0, DEFAULT_INTERVAL_MIN_HARD_DAYS),
        interval_min_good_days=_clamp_float(sched.get("interval_min_good_days"), 0.2, 2.0, DEFAULT_INTERVAL_MIN_GOOD_DAYS),
        interval_min_easy_days=_clamp_float(sched.get("interval_min_easy_days"), 0.5, 5.0, DEFAULT_INTERVAL_MIN_EASY_DAYS),
    )
    session = SessionConfig(
        new_cards_per_day_default=_clamp_int(sess.get("new_cards_per_day_default"), 0, 500, DEFAULT_NEW_CARDS_PER_DAY),
        estimated_seconds_per_review=_clamp_int(sess.get("estimated_seconds_per_review"), 5, 300, DEFAULT_ESTIMATED_SECONDS_PER_REVIEW),
        daily_goal_reviews_max=_clamp_int(sess.get("daily_goal_reviews_max"), 1, 2000, DEFAULT_DAILY_GOAL_REVIEWS_MAX),
        candidate_limit=_clamp_int(sess.get("candidate_limit"), 5, 200, DEFAULT_SESSION_CANDIDATE_LIMIT),
        due_now_threshold_full_stop=_clamp_int(sess.get("due_now_threshold_full_stop"), 50, 500, DEFAULT_DUE_NOW_THRESHOLD_FULL_STOP),
        due_now_threshold_cap_5=_clamp_int(sess.get("due_now_threshold_cap_5"), 20, 300, DEFAULT_DUE_NOW_THRESHOLD_CAP_5),
        due_now_threshold_cap_7=_clamp_int(sess.get("due_now_threshold_cap_7"), 10, 200, DEFAULT_DUE_NOW_THRESHOLD_CAP_7),
        due_now_threshold_cap_10=_clamp_int(sess.get("due_now_threshold_cap_10"), 5, 100, DEFAULT_DUE_NOW_THRESHOLD_CAP_10),
        leech_count_no_new=_clamp_int(sess.get("leech_count_no_new"), 3, 50, DEFAULT_LEECH_COUNT_NO_NEW),
        leech_count_cap_3=_clamp_int(sess.get("leech_count_cap_3"), 2, 20, DEFAULT_LEECH_COUNT_CAP_3),
        backlog_threshold=_clamp_int(sess.get("backlog_threshold"), 5, 100, DEFAULT_BACKLOG_THRESHOLD),
        backlog_very_high=_clamp_int(sess.get("backlog_very_high"), 20, 200, DEFAULT_BACKLOG_VERY_HIGH),
        backlog_overwhelming=_clamp_int(sess.get("backlog_overwhelming"), 50, 500, DEFAULT_BACKLOG_OVERWHELMING),
        pool_due_first_prob_very_high=_clamp_float(sess.get("pool_due_first_prob_very_high"), 0.5, 1.0, DEFAULT_POOL_DUE_FIRST_PROB_VERY_HIGH),
        pool_due_first_prob_high=_clamp_float(sess.get("pool_due_first_prob_high"), 0.5, 1.0, DEFAULT_POOL_DUE_FIRST_PROB_HIGH),
        pool_again_prob=_clamp_float(sess.get("pool_again_prob"), 0.0, 1.0, DEFAULT_POOL_AGAIN_PROB),
        pool_learning_prob=_clamp_float(sess.get("pool_learning_prob"), 0.0, 1.0, DEFAULT_POOL_LEARNING_PROB),
        pool_hard_prob=_clamp_float(sess.get("pool_hard_prob"), 0.0, 1.0, DEFAULT_POOL_HARD_PROB),
        pool_good_prob=_clamp_float(sess.get("pool_good_prob"), 0.0, 1.0, DEFAULT_POOL_GOOD_PROB),
        bandit_epsilon=_clamp_float(sess.get("bandit_epsilon"), 0.0, 1.0, DEFAULT_BANDIT_EPSILON),
        bandit_min_pulls_explore=_clamp_int(sess.get("bandit_min_pulls_explore"), 1, 20, DEFAULT_BANDIT_MIN_PULLS_EXPLORE),
        bandit_reward_time_cap_ms=_clamp_int(sess.get("bandit_reward_time_cap_ms"), 5000, 300_000, DEFAULT_BANDIT_REWARD_TIME_CAP_MS),
    )
    limits = LimitsConfig(
        list_cards_limit=_clamp_int(lim.get("list_cards_limit"), 10, 2000, DEFAULT_LIST_CARDS_LIMIT),
        search_examples_limit=_clamp_int(lim.get("search_examples_limit"), 10, 500, DEFAULT_SEARCH_EXAMPLES_LIMIT),
        search_examples_max=_clamp_int(lim.get("search_examples_max"), 50, 1000, DEFAULT_SEARCH_EXAMPLES_MAX),
        metrics_summary_default=_clamp_int(lim.get("metrics_summary_default"), 20, 2000, DEFAULT_METRICS_SUMMARY_DEFAULT),
        metrics_summary_min=_clamp_int(lim.get("metrics_summary_min"), 10, 500, DEFAULT_METRICS_SUMMARY_MIN),
        metrics_summary_max=_clamp_int(lim.get("metrics_summary_max"), 100, 10000, DEFAULT_METRICS_SUMMARY_MAX),
    )
    import_ = ImportConfig(
        max_rows_default=_clamp_int(imp.get("max_rows_default"), 1000, 1_000_000, DEFAULT_IMPORT_MAX_ROWS),
        max_cell_chars_default=_clamp_int(imp.get("max_cell_chars_default"), 1000, 100_000, DEFAULT_IMPORT_MAX_CELL_CHARS),
    )
    return StudyConfig(scheduler=scheduler, session=session, limits=limits, import_=import_)


_cached: StudyConfig | None = None


def get_study_config() -> StudyConfig:
    """Return study config (defaults + optional YAML overrides). Cached per process."""
    global _cached
    if _cached is None:
        _cached = _apply_overrides(_load_yaml_if_available())
    return _cached


def reload_study_config() -> StudyConfig:
    """Reload config from file (e.g. for tests)."""
    global _cached
    _cached = _apply_overrides(_load_yaml_if_available())
    return _cached
