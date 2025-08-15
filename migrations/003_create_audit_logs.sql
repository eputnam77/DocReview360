CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    user_id TEXT,
    action TEXT NOT NULL,
    entity_id TEXT,
    details JSON,
    severity TEXT,
    ip_address TEXT
);
