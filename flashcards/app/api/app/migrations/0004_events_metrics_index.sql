-- 0004_events_metrics_index.sql
-- Index for metrics summary query: WHERE user_id = ? AND event_type = 'answer_submitted'

CREATE INDEX IF NOT EXISTS idx_events_user_event_type ON events (user_id, event_type);
