from docreview360.database import Database
from docreview360.stubs.task251 import save_document


def test_task251_persists_version(tmp_path) -> None:
    db = Database("sqlite:///:memory:")
    db.migrate()
    with db.session() as session:
        assert save_document(session, "doc1", "hi") is True
