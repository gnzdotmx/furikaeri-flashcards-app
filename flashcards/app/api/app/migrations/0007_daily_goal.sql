-- 0007_daily_goal.sql
-- Optional daily review goal and support for streak (computed from events).

PRAGMA foreign_keys = ON;

ALTER TABLE users ADD COLUMN daily_goal_reviews INTEGER NULL;
