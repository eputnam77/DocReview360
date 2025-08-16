CREATE INDEX IF NOT EXISTS idx_audit_logs_entity_timestamp ON audit_logs (entity_id, timestamp);
