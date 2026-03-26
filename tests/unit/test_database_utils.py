from pathlib import Path

import pytest
from docreview360.database import (
    Database,
    _parse_sql_statements,
    default_url,
)
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError


def test_default_url_variants() -> None:
    assert default_url("sqlite") == "sqlite:///docreview360.db"
    assert default_url("PostgreSQL").startswith("postgresql+psycopg")
    assert default_url("mysql").startswith("mysql+pymysql")
    assert default_url("oracle").startswith("oracle+oracledb")
    with pytest.raises(ValueError):
        default_url("unsupported_db_xyz")


def test_parse_sql_statements_handles_triggers(tmp_path: Path) -> None:
    sql = (
        "-- comment\n"
        "CREATE TRIGGER trg\n"
        "AFTER INSERT ON t\n"
        "BEGIN\n"
        "  SELECT 1;\n"
        "END\n"
        ";\n"
        "CREATE TABLE other(id INTEGER)"
    )
    file = tmp_path / "m.sql"
    file.write_text(sql)
    stmts = _parse_sql_statements(file)
    assert stmts[0].startswith("CREATE TRIGGER")
    assert stmts[1] == "CREATE TABLE other(id INTEGER)"


def test_initialize_and_session() -> None:
    db = Database("sqlite:///:memory:")
    db.initialize()
    with db.session() as conn:
        conn.execute(text("CREATE TABLE x (id INTEGER PRIMARY KEY)"))
        conn.execute(text("INSERT INTO x (id) VALUES (1)"))
        assert conn.execute(text("SELECT id FROM x")).scalar() == 1


def test_apply_sql_migrations_paths(tmp_path: Path) -> None:
    good_dir = tmp_path / "good"
    good_dir.mkdir()
    (good_dir / "001.sql").write_text("CREATE TABLE t (id INTEGER);")
    bad_dir = tmp_path / "bad"
    bad_dir.mkdir()
    (bad_dir / "999.sql").write_text("INVALID SQL;")
    db = Database("sqlite:///:memory:")
    # nonexistent path should be ignored
    db._apply_sql_migrations(tmp_path / "missing")
    # recursion when conn is None
    db._apply_sql_migrations(good_dir)
    inspector = inspect(db._engine)
    assert "t" in inspector.get_table_names()
    with pytest.raises(OperationalError):
        db._apply_sql_migrations(bad_dir, db._engine.connect())


def test_drop_all_and_isolation(tmp_path: Path) -> None:
    mig = tmp_path / "migs"
    mig.mkdir()
    (mig / "001.sql").write_text("CREATE TABLE t (id INTEGER);")
    db1 = Database("sqlite:///:memory:")
    db1.migrate(migrations_path=mig)
    assert "t" in inspect(db1._engine).get_table_names()
    # new Database should be isolated and not see previous tables
    db2 = Database("sqlite:///:memory:")
    assert "t" not in inspect(db2._engine).get_table_names()
    # dropping all removes tables and version tracking
    db1.drop_all()
    assert "t" not in inspect(db1._engine).get_table_names()
