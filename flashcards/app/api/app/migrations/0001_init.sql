-- 0001_init.sql
-- Initial local-first schema for Furikaeri.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decks (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notes (
  id TEXT PRIMARY KEY,
  source_type TEXT NOT NULL, -- grammar | kanji | vocabulary
  level TEXT NOT NULL,       -- N5..N1 or custom
  key TEXT NOT NULL,         -- stable unique key within (source_type, level)
  fields_json TEXT NOT NULL, -- canonical fields + original fields (JSON serialized)
  source_url TEXT,
  created_at TEXT NOT NULL,
  UNIQUE (source_type, level, key)
);

CREATE INDEX IF NOT EXISTS idx_notes_source_level ON notes (source_type, level);
CREATE INDEX IF NOT EXISTS idx_notes_key ON notes (key);

CREATE TABLE IF NOT EXISTS cards (
  id TEXT PRIMARY KEY,
  note_id TEXT NOT NULL,
  deck_id TEXT NOT NULL,
  card_type TEXT NOT NULL,
  front_template TEXT,
  back_template TEXT,
  tags_json TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL,
  FOREIGN KEY (note_id) REFERENCES notes (id) ON DELETE CASCADE,
  FOREIGN KEY (deck_id) REFERENCES decks (id) ON DELETE CASCADE,
  UNIQUE (note_id, deck_id, card_type)
);

CREATE INDEX IF NOT EXISTS idx_cards_deck ON cards (deck_id);
CREATE INDEX IF NOT EXISTS idx_cards_note ON cards (note_id);

CREATE TABLE IF NOT EXISTS review_state (
  card_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  due_at TEXT NOT NULL,
  stability REAL NOT NULL DEFAULT 0,
  difficulty REAL NOT NULL DEFAULT 0,
  last_rating TEXT,
  lapses INTEGER NOT NULL DEFAULT 0,
  reps INTEGER NOT NULL DEFAULT 0,
  avg_time_ms INTEGER NOT NULL DEFAULT 0,
  streak INTEGER NOT NULL DEFAULT 0,
  leech_flag INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (card_id, user_id),
  FOREIGN KEY (card_id) REFERENCES cards (id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_review_due ON review_state (due_at);
CREATE INDEX IF NOT EXISTS idx_review_user ON review_state (user_id);

CREATE TABLE IF NOT EXISTS events (
  event_id TEXT PRIMARY KEY,
  ts TEXT NOT NULL,
  user_id TEXT NOT NULL,
  session_id TEXT,
  event_type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_events_user_ts ON events (user_id, ts);

