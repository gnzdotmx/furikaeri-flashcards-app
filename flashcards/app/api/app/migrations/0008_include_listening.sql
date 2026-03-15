-- 0008_include_listening.sql
-- Option to exclude listening (vocab_listening) cards from a session when user can't play sounds.

ALTER TABLE study_sessions ADD COLUMN include_listening INTEGER NOT NULL DEFAULT 1;
