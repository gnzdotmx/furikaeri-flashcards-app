-- 0002_sessions.sql
-- Study sessions + user settings (local-first)

PRAGMA foreign_keys = ON;

-- Basic user settings for scheduling knobs (single-user initially).
ALTER TABLE users ADD COLUMN new_cards_per_day INTEGER NOT NULL DEFAULT 10;
ALTER TABLE users ADD COLUMN target_retention REAL NOT NULL DEFAULT 0.9;

CREATE TABLE IF NOT EXISTS study_sessions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  deck_id TEXT NOT NULL,
  mode TEXT NOT NULL, -- e.g. "mixed"
  new_limit INTEGER NOT NULL,
  new_shown INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  ended_at TEXT,
  FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
  FOREIGN KEY (deck_id) REFERENCES decks (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_created ON study_sessions (user_id, created_at);

CREATE TABLE IF NOT EXISTS session_seen (
  session_id TEXT NOT NULL,
  card_id TEXT NOT NULL,
  seen_at TEXT NOT NULL,
  PRIMARY KEY (session_id, card_id),
  FOREIGN KEY (session_id) REFERENCES study_sessions (id) ON DELETE CASCADE,
  FOREIGN KEY (card_id) REFERENCES cards (id) ON DELETE CASCADE
);

