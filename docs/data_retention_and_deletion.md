# Data Retention and Deletion Policy

DocReview360 v0.1 applies explicit retention windows, immutable audit handling,
and a documented export-before-delete workflow for regulated operations.

## Retention Policy

Default retention windows:

- Operational logs: 365 days
- Archive artifacts and archive metadata: 365 days
- Compliance audit logs: 2555 days (7 years)

Retention values are configurable in `settings.yaml`:

```yaml
logs:
  retention_days: 365
  purge_interval_minutes: 1440
audit_log:
  retention_days: 2555
  purge_interval_minutes: 1440
archive:
  retention_days: 365
  purge_interval_minutes: 1440
```

Scheduled purge jobs remove records older than the configured threshold.

## Soft Delete vs Hard Delete

DocReview360 v0.1 uses **hard delete** for active object stores (for example,
projects, users, templates, and document types) when delete endpoints are
invoked.

DocReview360 v0.1 does **not** implement first-class soft-delete tombstones for
those active object types.

Operator expectation:

- Treat delete actions as destructive.
- Export and archive data before deletion.
- Use backup/restore for recovery.

## Audit Log Immutability and Retention

Audit events are append-only by policy and are retained based on
`audit_log.retention_days`.

Immutability posture:

- Audit records are written as append events.
- Integrity checks and hash-anchor workflows are used for tamper evidence.
- Audit retention purge is time-based only; ad-hoc business record deletion does
  not remove historical audit entries immediately.

## Export-Before-Delete Workflow

Before deleting projects/documents or configuration entities:

1. Export full instance backup:

```bash
docreview360 migrate export backup-pre-delete.json.gz
```

2. Export document/project artifacts needed for evidence:

- Use document export endpoints (Markdown/DOCX/PDF/JSON/XML).
- Use archive endpoints (`POST /archive/{doc_id}` and `GET /archive/...`) for
  immutable snapshots and reports.

3. Verify backup integrity and archive IDs.

4. Perform deletion only after backup and export artifacts are confirmed.

5. Record change ticket or approval reference for traceability.

## GDPR-Style Delete Handling

DocReview360 v0.1 supports GDPR-style requests operationally with these rules:

- Active profile/content records can be deleted through normal admin workflows.
- Audit/security logs are retained for configured compliance windows and may be
  minimized or pseudonymized operationally where legally required.
- Data subject requests should be processed with a documented case ID and legal
  basis.
- If full erasure conflicts with legal retention duties, retain only required
  fields for the minimum lawful period.

This policy is a product baseline and not legal advice.
