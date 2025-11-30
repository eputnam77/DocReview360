import pytest

from docreview360 import rbac
from docreview360.logs import (
    clear_logs,
    delete_log,
    log_event,
    purge_logs,
    query_logs,
)


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


def test_delete_log_requires_admin_and_logs_action() -> None:
    clear_logs()
    entry = log_event("alpha", user_id="bob")
    with pytest.raises(PermissionError):
        delete_log(entry.id, "bob")
    rbac.add_role("alice", "admin")
    removed = delete_log(entry.id, "alice", reason="cleanup")
    assert removed is True
    entries = query_logs()
    actions = {e.action for e in entries}
    assert "log_deleted" in actions
    assert all(e.id != entry.id for e in entries if e.action != "log_deleted")
    clear_logs()
