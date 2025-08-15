from docreview360.audit import (
    clear_audit_log,
    get_audit_entry,
    get_audit_log,
    log_audit_event,
)
from docreview360.logs import clear_logs, log_event, query_logs


def test_query_logs_sorted_and_id_lookup() -> None:
    clear_logs()
    e1 = log_event("alpha", user_id="u")
    e2 = log_event("beta", user_id="u")
    logs = query_logs(user_id="u")
    assert [logs[0].id, logs[1].id] == [e1.id, e2.id]
    found = query_logs(log_id=e1.id)
    assert len(found) == 1 and found[0].id == e1.id


def test_audit_log_sort_and_lookup() -> None:
    clear_audit_log()
    doc_id = "doc"
    a1 = log_audit_event(doc_id, "first")
    a2 = log_audit_event(doc_id, "second")
    events = get_audit_log(doc_id)
    assert [events[0].id, events[1].id] == [a1.id, a2.id]
    fetched = get_audit_entry(a1.id)
    assert fetched is not None and fetched.id == a1.id
