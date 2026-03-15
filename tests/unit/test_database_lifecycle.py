from pathlib import Path

import pytest
from sqlalchemy import text

from docreview360.database import Database, default_url


def test_database_lifecycle(tmp_path: Path) -> None:
    db = Database("sqlite:///:memory:")
    db.initialize()
    with db.session() as conn:
        conn.execute(text("SELECT 1"))
    mig_dir = tmp_path / "migs"
    mig_dir.mkdir()
    (mig_dir / "001.sql").write_text("CREATE TABLE demo(id INT);")
    db.migrate(mig_dir)
    db.migrate(mig_dir)  # re-run to hit already applied branch
    db._apply_sql_migrations(tmp_path / "missing")  # nonexistent path
    Database("postgresql+psycopg://user:pass@localhost/testdb")  # non-sqlite branch
    with pytest.raises(ValueError):
        Database("")
    with pytest.raises(ValueError):
        default_url("unsupported_db_xyz")
    db.drop_all()
