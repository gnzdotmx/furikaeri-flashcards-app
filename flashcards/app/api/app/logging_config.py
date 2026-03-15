"""Logging setup: format, level from LOG_LEVEL, no passwords/tokens/PII in log messages."""

import logging
import os
import sys


def configure(
    *,
    level: str | int | None = None,
    format_string: str | None = None,
) -> None:
    """Set up root logger. Idempotent: first call wins."""
    root = logging.getLogger()
    if root.handlers:
        return

    if level is None:
        level = os.environ.get("LOG_LEVEL", "INFO").upper()
    if isinstance(level, str):
        level = getattr(logging, level, logging.INFO)

    if format_string is None:
        format_string = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    formatter = logging.Formatter(format_string, datefmt="%Y-%m-%dT%H:%M:%S")

    handler: logging.Handler
    if sys.stderr.isatty():
        handler = logging.StreamHandler(sys.stderr)
    else:
        handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(level)
    root.addHandler(handler)
    root.setLevel(level)

    # uvicorn.access is noisy at INFO
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
