import pytest

from docreview360.logs import clear_logs, log_call, logs


def test_log_call_success_redacts_sensitive_data() -> None:
    clear_logs()

    @log_call
    def sample(password: str) -> str:
        return "ok"

    sample(password="secret")
    entry = logs[-1]
    assert entry.severity == "info"
    assert entry.details["kwargs"]["password"] == "'[REDACTED]'"


def test_log_call_failure_logs_stacktrace_and_error_severity() -> None:
    clear_logs()

    @log_call
    def boom(token: str) -> None:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        boom(token="abc123")

    entry = logs[-1]
    assert entry.severity == "error"
    assert entry.details["kwargs"]["token"] == "'[REDACTED]'"
    assert "RuntimeError" in entry.details["stacktrace"]
