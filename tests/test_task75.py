from docuflow.logs import clear_logs, log_event
from docuflow.stubs.task75 import register_log_alert


def test_alert_triggered_on_pattern() -> None:
    triggered = []

    def cb(entry):
        triggered.append(entry.action)

    register_log_alert("error", cb)
    clear_logs()
    log_event("user_error")
    assert triggered == ["user_error"]
