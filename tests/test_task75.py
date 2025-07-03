from docuflow.logs import clear_logs, log_event, register_alert


def test_alert_triggered_on_pattern() -> None:
    triggered = []

    def cb(entry):
        triggered.append(entry.action)

    register_alert("error", cb)
    clear_logs()
    log_event("user_error")
    assert triggered == ["user_error"]
