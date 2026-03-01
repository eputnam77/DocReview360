# Data Model and Migration Policy

This document defines the v0.1 migration discipline for DocReview360.

## Tooling and version pinning

- Migration execution uses `docreview360.database.Database.migrate`.
- Raw SQL migrations are loaded from the repository `migrations/` directory.
- Migration files are ordered lexicographically by zero-padded numeric prefix (for example `007_add_audit_log_entity_type.sql`).
- Runtime and database driver versions are pinned in `pyproject.toml` and `poetry.lock`.

## Forward-only migration policy

- Migrations are forward-only.
- Existing migration files are immutable after release.
- New schema changes must be introduced as a new migration file; never rewrite previously shipped migrations.
- All migrations must be idempotent enough for safe re-run detection through `schema_versions` tracking.

## Rollback policy

- DocReview360 does not provide destructive SQL downgrades in v0.1.
- Rollback is performed by restoring from validated backups (see `docs/disaster_recovery.md`).
- CI includes a migration failure-recovery test to ensure failed batches are not version-tracked and can be safely retried.

## Schema compatibility guarantees

- CI includes an explicit upgrade-path test from a v0.0.x-style migration set (`001`-`005`) to v0.1.
- Upgrade tests verify existing audit rows remain queryable after schema extension.

## Supported database engines (v0.1)

DocReview360 supports these SQLAlchemy backends for v0.1 deployments:

- SQLite (default local deployment path).
- PostgreSQL via `psycopg`.
- MySQL via `pymysql`.

Recommended production baselines:

- PostgreSQL 14+
- MySQL 8.0+

SQLite is primarily intended for local development, CI, and single-node testing.

## SemVer and schema-breaking changes

- Schema-breaking database changes require a **MAJOR** version bump.
- Backward-compatible additive schema changes are released as MINOR/PATCH with forward migration files.
- Release notes must call out any schema-impacting change and required upgrade steps.
