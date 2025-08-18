ALTER TABLE audit_logs ADD COLUMN entity_type TEXT;
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity_type ON audit_logs (entity_type);
