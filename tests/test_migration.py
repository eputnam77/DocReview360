from docuflow.database import Database
from sqlalchemy import inspect


def test_database_migrate() -> None:
    db = Database("sqlite:///:memory:")
    db.migrate()
    inspector = inspect(db._engine)
    assert set(inspector.get_table_names()) >= {"documents", "projects"}
