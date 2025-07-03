from pathlib import Path

from sqlalchemy import inspect, text

from docuflow.database import Database


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
