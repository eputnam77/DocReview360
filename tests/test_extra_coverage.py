from docuflow.logs import clear_logs, export_logs, log_event


def test_export_logs_counts() -> None:
    clear_logs()
    log_event("a")
    log_event("b")
    assert len(export_logs()) == 2
