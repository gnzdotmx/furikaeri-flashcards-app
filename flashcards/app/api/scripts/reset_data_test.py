"""Tests for scripts/reset_data.py.

Verifies that reset_all_data clears all tables in FK-safe order (e.g. auth_sessions
before users) so that PRAGMA foreign_keys = ON does not cause delete failures.
"""

import os
import tempfile

from app.db import connection, ensure_db, run_migrations

# Import after path setup so script module can load app
from scripts import reset_data


def test_reset_all_data_clears_auth_sessions_before_users() -> None:
    """With FK on, deleting users would fail if auth_sessions were not deleted first."""
    tmp = tempfile.mkdtemp(prefix="furikaeri_reset_test_")
    path = os.path.join(tmp, "db.sqlite")
    try:
        ensure_db(path)
        run_migrations(path)

        with connection(path) as conn:
            conn.execute(
                "INSERT INTO users (id, created_at) VALUES (?, ?);",
                ("user-1", "2025-01-01T00:00:00Z"),
            )
            conn.execute(
                "INSERT INTO auth_sessions (jti, user_id, created_at, expires_at) VALUES (?, ?, ?, ?);",
                ("jti-1", "user-1", 1704067200, 1704153600),
            )
            conn.commit()

        reset_data.reset_all_data(path)

        with connection(path) as conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            users_count = conn.execute("SELECT COUNT(*) AS n FROM users;").fetchone()[0]
            sessions_count = conn.execute(
                "SELECT COUNT(*) AS n FROM auth_sessions;"
            ).fetchone()[0]
        assert users_count == 0
        assert sessions_count == 0
    finally:
        if os.path.isfile(path):
            os.remove(path)
        os.rmdir(tmp)


def test_reset_all_data_clears_all_tables() -> None:
    """Reset leaves core tables empty (smoke test for full delete order)."""
    tmp = tempfile.mkdtemp(prefix="furikaeri_reset_test_")
    path = os.path.join(tmp, "db.sqlite")
    try:
        ensure_db(path)
        run_migrations(path)

        with connection(path) as conn:
            conn.execute(
                "INSERT INTO users (id, created_at) VALUES (?, ?);",
                ("u1", "2025-01-01T00:00:00Z"),
            )
            conn.execute(
                "INSERT INTO auth_sessions (jti, user_id, created_at, expires_at) VALUES (?, ?, ?, ?);",
                ("j", "u1", 1704067200, 1704153600),
            )
            conn.commit()

        reset_data.reset_all_data(path)

        # Tables cleared by reset_all_data (allowlisted; do not use user input for table names)
        tables_cleared = (
            "session_seen",
            "study_sessions",
            "review_state",
            "cards",
            "notes",
            "decks",
            "events",
            "bandit_state",
            "user_prefs",
            "user_fsrs_params",
            "auth_sessions",
            "users",
        )
        with connection(path) as conn:
            for table in tables_cleared:
                row = conn.execute(
                    "SELECT COUNT(*) AS n FROM " + table + ";"
                ).fetchone()
                assert row[0] == 0, f"Expected {table} to be empty after reset"
    finally:
        if os.path.isfile(path):
            os.remove(path)
        os.rmdir(tmp)


def test_reset_all_data_idempotent_on_empty_db() -> None:
    """Calling reset on an already empty DB does not raise."""
    tmp = tempfile.mkdtemp(prefix="furikaeri_reset_test_")
    path = os.path.join(tmp, "db.sqlite")
    try:
        ensure_db(path)
        run_migrations(path)
        reset_data.reset_all_data(path)
        reset_data.reset_all_data(path)
    finally:
        if os.path.isfile(path):
            os.remove(path)
        os.rmdir(tmp)
