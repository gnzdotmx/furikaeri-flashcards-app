"""Tests for app.study_config."""

import os
import tempfile
from pathlib import Path

from app import study_config
from app.study_config import (
    DEFAULT_LEARNING_STEPS_MINUTES,
    DEFAULT_TARGET_RETENTION,
    get_study_config,
    reload_study_config,
)


def test_get_study_config_returns_defaults_without_yaml():
    """Without STUDY_CONFIG_PATH or study_config.yaml, defaults are used."""
    # Clear env so we don't load a user's file
    old = os.environ.pop("STUDY_CONFIG_PATH", None)
    try:
        reload_study_config()
        cfg = get_study_config()
        assert cfg.scheduler.target_retention == DEFAULT_TARGET_RETENTION
        assert cfg.scheduler.learning_steps_minutes == DEFAULT_LEARNING_STEPS_MINUTES
        assert cfg.scheduler.leech_lapses_threshold == 8
        assert cfg.scheduler.again_review_minutes == 10
        assert cfg.session.new_cards_per_day_default == 10
        assert cfg.session.daily_goal_reviews_max == 500
        assert cfg.session.backlog_threshold == 30
        assert cfg.limits.list_cards_limit == 200
        assert cfg.limits.search_examples_limit == 80
        assert cfg.import_.max_rows_default == 50_000
        assert cfg.import_.max_cell_chars_default == 20_000
    finally:
        if old is not None:
            os.environ["STUDY_CONFIG_PATH"] = old
        reload_study_config()


def test_get_study_config_loads_yaml_override():
    """With STUDY_CONFIG_PATH pointing to YAML, overrides are applied."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("""
scheduler:
  target_retention: 0.85
  learning_steps_minutes: [2, 15]
  leech_lapses_threshold: 6
  again_review_minutes: 5
session:
  new_cards_per_day_default: 20
  daily_goal_reviews_max: 300
  backlog_threshold: 25
limits:
  list_cards_limit: 100
import:
  max_rows_default: 10_000
  max_cell_chars_default: 5_000
""")
        path = f.name
    try:
        study_config._cached = None
        os.environ["STUDY_CONFIG_PATH"] = path
        cfg = reload_study_config()
        assert cfg.scheduler.target_retention == 0.85
        assert cfg.scheduler.learning_steps_minutes == (2, 15)
        assert cfg.scheduler.leech_lapses_threshold == 6
        assert cfg.scheduler.again_review_minutes == 5
        assert cfg.session.new_cards_per_day_default == 20
        assert cfg.session.daily_goal_reviews_max == 300
        assert cfg.session.backlog_threshold == 25
        assert cfg.limits.list_cards_limit == 100
        assert cfg.import_.max_rows_default == 10_000
        assert cfg.import_.max_cell_chars_default == 5_000
    finally:
        os.environ.pop("STUDY_CONFIG_PATH", None)
        Path(path).unlink(missing_ok=True)
        reload_study_config()


def test_get_study_config_clamps_invalid_yaml_values():
    """Invalid or out-of-range YAML values are clamped to safe defaults."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("""
scheduler:
  target_retention: 0.2
  leech_lapses_threshold: 100
session:
  new_cards_per_day_default: -5
  daily_goal_reviews_max: 99999
""")
        path = f.name
    try:
        study_config._cached = None
        os.environ["STUDY_CONFIG_PATH"] = path
        cfg = reload_study_config()
        # target_retention clamped to 0.5..0.99
        assert cfg.scheduler.target_retention == 0.5
        # leech_lapses_threshold clamped to 3..20
        assert cfg.scheduler.leech_lapses_threshold == 20
        # new_cards_per_day_default clamped to 0..500
        assert cfg.session.new_cards_per_day_default == 0
        # daily_goal_reviews_max clamped to 1..2000
        assert cfg.session.daily_goal_reviews_max == 2000
    finally:
        os.environ.pop("STUDY_CONFIG_PATH", None)
        Path(path).unlink(missing_ok=True)
        reload_study_config()


def test_get_study_config_missing_file_uses_defaults():
    """Non-existent path falls back to defaults."""
    os.environ["STUDY_CONFIG_PATH"] = "/nonexistent/study_config_does_not_exist.yaml"
    try:
        reload_study_config()
        cfg = get_study_config()
        assert cfg.scheduler.target_retention == DEFAULT_TARGET_RETENTION
        assert cfg.session.new_cards_per_day_default == 10
    finally:
        os.environ.pop("STUDY_CONFIG_PATH", None)
        reload_study_config()
