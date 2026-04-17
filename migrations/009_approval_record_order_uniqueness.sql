ALTER TABLE approval_records ADD COLUMN phase_id TEXT NOT NULL DEFAULT '';
ALTER TABLE approval_records ADD COLUMN approval_order INTEGER NOT NULL DEFAULT 0;
UPDATE approval_records
SET
    phase_id = COALESCE(NULLIF(json_extract(data, '$.phase_id'), 'null'), ''),
    approval_order = COALESCE(CAST(json_extract(data, '$.order') AS INTEGER), 0)
WHERE phase_id = '' AND approval_order = 0;
CREATE UNIQUE INDEX IF NOT EXISTS uq_approval_records_workflow_phase_order
ON approval_records (workflow_id, phase_id, approval_order)
WHERE approval_order <> 0;
