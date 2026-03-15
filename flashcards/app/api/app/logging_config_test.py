"""Tests for app.logging_config."""

import logging

from app.logging_config import configure


def test_configure_sets_root_logger_level_and_handler():
    # Clear any existing handlers so configure() adds one
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.NOTSET)
    try:
        configure(level=logging.DEBUG)
        assert root.level == logging.DEBUG
        assert len(root.handlers) == 1
        assert root.handlers[0].level == logging.DEBUG
    finally:
        root.handlers.clear()
        root.setLevel(logging.WARNING)


def test_configure_idempotent_when_called_twice():
    root = logging.getLogger()
    root.handlers.clear()
    try:
        configure(level=logging.INFO)
        n = len(root.handlers)
        configure(level=logging.WARNING)
        assert len(root.handlers) == n, "configure should not add duplicate handlers"
    finally:
        root.handlers.clear()


def test_configure_accepts_level_string():
    root = logging.getLogger()
    root.handlers.clear()
    try:
        configure(level="ERROR")
        assert root.level == logging.ERROR
    finally:
        root.handlers.clear()


def test_configure_uses_env_when_level_none(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    root = logging.getLogger()
    root.handlers.clear()
    try:
        configure(level=None)
        assert root.level == logging.DEBUG
    finally:
        root.handlers.clear()
        monkeypatch.delenv("LOG_LEVEL", raising=False)
