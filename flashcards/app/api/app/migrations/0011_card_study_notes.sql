-- Per-user personal note for a flashcard (one row per user+card; separate from content `notes` table).

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS card_study_notes (
  user_id TEXT NOT NULL,
  card_id TEXT NOT NULL,
  body TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (user_id, card_id),
  FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
  FOREIGN KEY (card_id) REFERENCES cards (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_card_study_notes_card ON card_study_notes (card_id);
