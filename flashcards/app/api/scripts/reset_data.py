#!/usr/bin/env python3
"""Reset deck data (decks, cards, notes, review state, sessions, auth). Run from api/: python scripts/reset_data.py"""
import os
import sys

# Allow running from api/ or api/scripts/
_API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _API_DIR not in sys.path:
    sys.path.insert(0, _API_DIR)

from app.db import connection  # noqa: E402
from app.settings import load_settings  # noqa: E402


def reset_all_data(sqlite_path: str) -> None:
    """Clear decks, cards, notes, review state, sessions, auth (FK order: children before parents)."""
    with connection(sqlite_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("DELETE FROM session_seen;")
        conn.execute("DELETE FROM study_sessions;")
        conn.execute("DELETE FROM review_state;")
        conn.execute("DELETE FROM cards;")
        conn.execute("DELETE FROM notes;")
        conn.execute("DELETE FROM decks;")
        conn.execute("DELETE FROM events;")
        conn.execute("DELETE FROM bandit_state;")
        conn.execute("DELETE FROM user_prefs;")
        conn.execute("DELETE FROM user_fsrs_params;")
        # Auth: sessions reference users; delete before users (migration 0010)
        conn.execute("DELETE FROM auth_sessions;")
        conn.execute("DELETE FROM users;")
        conn.commit()
    print("All deck and user data has been reset.")


def main() -> None:
    settings = load_settings()
    path = settings.sqlite_path
    if not os.path.isfile(path):
        print(f"Database file not found: {path}")
        print("Nothing to reset.")
        sys.exit(0)
    confirm = input(f"Reset all data in {path}? Type 'yes' to confirm: ")
    if confirm.strip().lower() not in ("yes", "y"):
        print("Aborted.")
        sys.exit(1)
    reset_all_data(path)


if __name__ == "__main__":
    main()
