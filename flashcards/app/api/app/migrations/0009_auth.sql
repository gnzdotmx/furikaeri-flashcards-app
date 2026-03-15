-- 0009_auth.sql
-- Auth columns for register/login. Existing rows (single-user) keep NULL; new users get username/email/password_hash.

PRAGMA foreign_keys = ON;

ALTER TABLE users ADD COLUMN username TEXT NULL;
ALTER TABLE users ADD COLUMN email TEXT NULL;
ALTER TABLE users ADD COLUMN password_hash TEXT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users (username) WHERE username IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users (email) WHERE email IS NOT NULL;
