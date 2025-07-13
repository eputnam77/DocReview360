from docreview360.logs import (
    LogEntry,
    clear_logs,
    log_event,
    register_listener,
    unregister_listener,
)


def test_live_log_listener() -> None:
    received = []

    def callback(entry: LogEntry) -> None:
        received.append(entry.action)

    register_listener(callback)
    clear_logs()
    log_event("create", user="u")
    unregister_listener(callback)
    log_event("ignore", user="u")

    assert received == ["create"]
