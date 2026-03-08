-- Migration 008: Add phases/phase_workflow_links tables and extend document_types
-- Replaces JSON-file persistence with database-backed storage for phases and
-- document types (Tier 2a).

-- Extend document_types with template/workflow/ordering columns.
-- SQLite supports ADD COLUMN only for nullable or DEFAULT-bearing columns.
ALTER TABLE document_types ADD COLUMN template TEXT NOT NULL DEFAULT '';
ALTER TABLE document_types ADD COLUMN workflow TEXT NOT NULL DEFAULT '[]';
ALTER TABLE document_types ADD COLUMN display_order INTEGER NOT NULL DEFAULT 0;
ALTER TABLE document_types ADD COLUMN default_template_id TEXT;

-- Phases table with ordering
CREATE TABLE IF NOT EXISTS phases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    display_order INTEGER NOT NULL DEFAULT 0
);

-- Phase → workflow-template link (at most one template per phase)
CREATE TABLE IF NOT EXISTS phase_workflow_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phase_id INTEGER NOT NULL UNIQUE REFERENCES phases(id) ON DELETE CASCADE,
    workflow_template_id TEXT NOT NULL
);

-- Seed the 9 default phases (INSERT OR IGNORE is idempotent on re-runs)
INSERT OR IGNORE INTO phases (name, display_order) VALUES
    ('Beta Documentation Review',         1),
    ('Draft Development',                 2),
    ('Final Issuance',                    3),
    ('General Availability',              4),
    ('Internal Coordination',             5),
    ('Maintenance / Revision Cycle',      6),
    ('Peer Review',                       7),
    ('Public Comment / Proposed Rulemaking', 8),
    ('Release Candidate Review',          9);
