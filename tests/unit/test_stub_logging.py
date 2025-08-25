import pytest

from docreview360.stubs import record_task_completion


def test_record_task_completion_suppresses_logging_errors(monkeypatch):
    calls = []

    def boom(*args, **kwargs):  # pragma: no cover - exercised via wrapper
        calls.append((args, kwargs))
        raise RuntimeError("db down")

    monkeypatch.setattr("docreview360.stubs.log_event", boom)

    # Should not raise despite log_event exploding
    record_task_completion(999)
    assert calls  # ensure our stub was actually invoked
