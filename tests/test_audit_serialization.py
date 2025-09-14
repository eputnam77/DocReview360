from datetime import datetime

from docreview360.audit import clear_audit_log, get_audit_log, log_audit_event


def test_log_audit_event_handles_non_json_context() -> None:
    """log_audit_event should serialise non-JSON types in context."""
    clear_audit_log()
    # ``datetime`` is not JSON serialisable by default.  The logging helper
    # should handle it transparently.
    log_audit_event("doc", "evt", when=datetime(2024, 1, 2))
    events = get_audit_log("doc")
    assert events and events[0].context["when"].startswith("2024-01-02")
