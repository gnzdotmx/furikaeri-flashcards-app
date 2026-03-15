-- 0006_suspended.sql
-- Suspend leeches: exclude from sessions until manually unsuspended.

PRAGMA foreign_keys = ON;

ALTER TABLE review_state ADD COLUMN suspended INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_review_suspended ON review_state (user_id, suspended) WHERE suspended = 1;
