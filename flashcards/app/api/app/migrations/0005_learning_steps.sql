-- 0005_learning_steps.sql
-- Learning steps for new cards: step index (0, 1, ...) or -1 when graduated.

PRAGMA foreign_keys = ON;

ALTER TABLE review_state ADD COLUMN learning_step INTEGER NOT NULL DEFAULT -1;

CREATE INDEX IF NOT EXISTS idx_review_learning_due ON review_state (learning_step, due_at) WHERE learning_step >= 0;
