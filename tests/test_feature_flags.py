import pytest
from docreview360 import db_store, feature_flags


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path) -> None:
    db_store.reset_db(f"sqlite:///{tmp_path / 'docreview360.db'}")
    yield
    db_store.reset_db(None)


def test_feature_flag_enabled() -> None:
    db = db_store.get_db()
    with db.orm_session() as session:
        feature_flags.set_flag(session, "beta_editor", enabled=True, org_id="org-1")
        assert feature_flags.is_flag_enabled(session, "beta_editor", org_id="org-1") is True
        assert feature_flags.is_flag_enabled(session, "beta_editor", org_id="org-2") is False


def test_feature_flags_missing() -> None:
    db = db_store.get_db()
    with db.orm_session() as session:
        assert feature_flags.is_flag_enabled(session, "completely_unknown_flag_xyz") is False
