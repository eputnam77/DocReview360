from pathlib import Path

from sqlalchemy import inspect, text

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
