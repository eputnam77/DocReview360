from hypothesis import given
from hypothesis import strategies as st
from sqlalchemy import text

from docuflow.database import Database


@given(st.none())
def test_task27_property(_):
    db = Database("sqlite:///:memory:")
    db.initialize()
    with db.session() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1
