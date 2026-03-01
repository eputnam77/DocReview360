from pathlib import Path

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from docreview360.database import Database


def test_sql_migrations(tmp_path: Path) -> None:
    """Migrations apply once and record their version."""
    mig = tmp_path / "migs"
    mig.mkdir()
    (mig / "001_add_table.sql").write_text("CREATE TABLE test_table (id INTEGER PRIMARY KEY);")

    db = Database("sqlite:///:memory:")
    db.migrate(migrations_path=mig)

    inspector = inspect(db._engine)
    assert "test_table" in inspector.get_table_names()
    assert "schema_versions" in inspector.get_table_names()

    # running again should not duplicate
    db.migrate(migrations_path=mig)
    with db._engine.begin() as conn:
        result = conn.execute(
            text("SELECT COUNT(*) FROM schema_versions WHERE filename='001_add_table.sql'")
        )
        assert result.scalar() == 1


def test_migration_adds_entity_type(tmp_path: Path) -> None:
    """Adding new migrations should modify existing tables."""
    old = tmp_path / "old_migs"
    old.mkdir()
    # copy initial migrations excluding the new one
    for file in sorted((Path("migrations") / "").glob("00[1-5]_*.sql")):
        (old / file.name).write_text(file.read_text())

    db_path = tmp_path / "test.db"
    db = Database(f"sqlite:///{db_path}")
    db.migrate(migrations_path=old)

    inspector = inspect(db._engine)
    cols = {c["name"] for c in inspector.get_columns("audit_logs")}
    assert "entity_type" in cols
    with db._engine.begin() as conn:
        applied = {row[0] for row in conn.execute(text("SELECT filename FROM schema_versions"))}
    assert "007_add_audit_log_entity_type.sql" not in applied

    # applying full migrations should record the new migration
    db.migrate()
    with db._engine.begin() as conn:
        applied = {row[0] for row in conn.execute(text("SELECT filename FROM schema_versions"))}
    assert "007_add_audit_log_entity_type.sql" in applied


def test_migration_failure_recovery_behaves_like_rollback(tmp_path: Path) -> None:
    """Failed migration batches should not be version-tracked and can be retried safely."""

    mig = tmp_path / "migs"
    mig.mkdir()
    (mig / "001_create_probe.sql").write_text(
        "CREATE TABLE migration_probe_one (id INTEGER PRIMARY KEY);"
    )
    (mig / "002_broken.sql").write_text("THIS IS INVALID SQL;")

    db = Database("sqlite:///:memory:")
    with pytest.raises(OperationalError):
        db.migrate(migrations_path=mig)

    # Even if SQLite auto-commits some DDL, failed batches must not be marked applied.
    with db._engine.begin() as conn:
        applied_after_failure = {
            row[0] for row in conn.execute(text("SELECT filename FROM schema_versions"))
        }
    assert "001_create_probe.sql" not in applied_after_failure
    assert "002_broken.sql" not in applied_after_failure

    # Fixing the bad migration and rerunning should apply and track both files.
    (mig / "002_broken.sql").write_text(
        "CREATE TABLE migration_probe_two (id INTEGER PRIMARY KEY);"
    )
    db.migrate(migrations_path=mig)

    inspector = inspect(db._engine)
    assert "migration_probe_one" in inspector.get_table_names()
    assert "migration_probe_two" in inspector.get_table_names()
    with db._engine.begin() as conn:
        applied_after_recovery = {
            row[0] for row in conn.execute(text("SELECT filename FROM schema_versions"))
        }
    assert "001_create_probe.sql" in applied_after_recovery
    assert "002_broken.sql" in applied_after_recovery


def test_schema_compatibility_upgrade_v0_0_x_to_v0_1(tmp_path: Path) -> None:
    """A v0.0.x-style schema should upgrade to v0.1 without losing existing audit rows."""

    legacy = tmp_path / "legacy_migs"
    legacy.mkdir()
    for file in sorted(Path("migrations").glob("00[1-5]_*.sql")):
        (legacy / file.name).write_text(file.read_text())

    db_path = tmp_path / "upgrade.db"
    db = Database(f"sqlite:///{db_path}")
    db.migrate(migrations_path=legacy)

    with db._engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO audit_logs (
                    id, timestamp, user_id, action, entity_id, details, severity, ip_address,
                    prev_hash, hash, document_hash, provider_response
                ) VALUES (
                    :id, :timestamp, :user_id, :action, :entity_id, :details, :severity,
                    :ip_address, :prev_hash, :hash, :document_hash, :provider_response
                )
                """
            ),
            {
                "id": "legacy-audit-1",
                "timestamp": "2026-02-01T00:00:00+00:00",
                "user_id": "alice",
                "action": "created",
                "entity_id": "doc-1",
                "details": "{}",
                "severity": "info",
                "ip_address": "127.0.0.1",
                "prev_hash": "",
                "hash": "",
                "document_hash": "",
                "provider_response": "{}",
            },
        )

    # Upgrade to full v0.1 migration set.
    db.migrate()

    inspector = inspect(db._engine)
    columns = {column["name"] for column in inspector.get_columns("audit_logs")}
    assert "entity_type" in columns

    with db._engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT id, action, entity_type FROM audit_logs WHERE id = 'legacy-audit-1'"
            )
        ).fetchone()
        applied = {row[0] for row in conn.execute(text("SELECT filename FROM schema_versions"))}

    assert row is not None
    assert row[0] == "legacy-audit-1"
    assert row[1] == "created"
    assert row[2] is None
    assert "007_add_audit_log_entity_type.sql" in applied
