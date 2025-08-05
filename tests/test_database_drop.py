from sqlalchemy import inspect

from docreview360.database import Database


def test_drop_all() -> None:
    db = Database("sqlite:///:memory:")
    db.migrate()
    db.drop_all()
    inspector = inspect(db._engine)
    assert "schema_versions" not in inspector.get_table_names()
