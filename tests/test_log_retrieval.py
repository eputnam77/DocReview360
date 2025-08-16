import uuid
from datetime import datetime, timezone

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


def test_log_event_timestamp_and_uuid() -> None:
    clear_logs()
    entry = log_event("alpha")
    uuid.UUID(entry.id)
    assert entry.timestamp.tzinfo == timezone.utc
    assert entry.timestamp.isoformat().endswith("+00:00")


def test_audit_log_sort_and_lookup() -> None:
    clear_audit_log()
    doc_id = "doc"
    a1 = log_audit_event(doc_id, "first")
    a2 = log_audit_event(doc_id, "second")
    events = get_audit_log(doc_id)
    assert [events[0].id, events[1].id] == [a1.id, a2.id]
    fetched = get_audit_entry(a1.id)
    assert fetched is not None and fetched.id == a1.id


def test_query_logs_filters_and_pagination() -> None:
    clear_logs()
    log_event(
        "alpha", user_id="u1", entity_id="d1", entity_type="doc", severity="info"
    )
    mid = datetime.now(timezone.utc)
    e2 = log_event(
        "beta", user_id="u2", entity_id="d2", entity_type="doc", severity="error"
    )
    after = datetime.now(timezone.utc)
    logs = query_logs(
        start=mid,
        end=after,
        user_id="u2",
        entity_id="d2",
        entity_type="doc",
        action="beta",
        severity="error",
    )
    assert [entry.id for entry in logs] == [e2.id]
    paged = query_logs(limit=1, offset=1)
    assert len(paged) == 1
