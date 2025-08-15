import pytest
from sqlalchemy import delete, update

from docreview360.logs import clear_logs, log_event, purge_logs, query_logs, _get_db
from docreview360.models import AuditLog
from docreview360 import rbac


def test_audit_log_is_immutable() -> None:
    clear_logs()
    log_event("alpha", user_id="bob")
    db = _get_db()
    with pytest.raises(PermissionError):
        with db.session() as conn:
            conn.execute(delete(AuditLog))
    with pytest.raises(PermissionError):
        with db.session() as conn:
            conn.execute(update(AuditLog).values(action="beta"))
    clear_logs()


def test_purge_logs_requires_admin_and_logs() -> None:
    clear_logs()
    log_event("alpha", user_id="bob")
    with pytest.raises(PermissionError):
        purge_logs("bob")
    rbac.add_role("alice", "admin")
    log_event("beta", user_id="alice")
    removed = purge_logs("alice", reason="cleanup")
    assert removed >= 2
    entries = query_logs()
    assert entries and entries[-1].action == "logs_purged"
    clear_logs()
