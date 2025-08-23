from docreview360.logs import LogEntry, clear_logs, log_event
from docreview360.stubs.task75 import register_log_alert


def test_alert_triggered_on_pattern() -> None:
    triggered = []

    def cb(entry: LogEntry) -> None:
        triggered.append(entry.action)

    clear_logs()
    register_log_alert("error", cb)
    log_event("user_error")
    assert triggered == ["user_error"]
