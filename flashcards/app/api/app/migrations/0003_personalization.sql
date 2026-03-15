-- 0003_personalization.sql
-- Privacy settings, bandits, and lightweight per-user scheduler params.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS user_prefs (
  user_id TEXT PRIMARY KEY,
  local_only INTEGER NOT NULL DEFAULT 1,
  cloud_sync_enabled INTEGER NOT NULL DEFAULT 0,
  encrypt_at_rest INTEGER NOT NULL DEFAULT 0,
  prefs_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS bandit_state (
  user_id TEXT NOT NULL,
  experiment_key TEXT NOT NULL,
  arm_key TEXT NOT NULL,
  pulls INTEGER NOT NULL DEFAULT 0,
  reward_sum REAL NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (user_id, experiment_key, arm_key),
  FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_fsrs_params (
  user_id TEXT PRIMARY KEY,
  stability_multiplier REAL NOT NULL DEFAULT 1.0,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

