from typing import Any

from docreview360.stubs.task99 import task99


def test_task99_completed(monkeypatch: Any) -> None:
    called: list[int] = []

    def record_completion(x: int) -> None:
        called.append(x)

    monkeypatch.setattr("docreview360.stubs.task99.record_task_completion", record_completion)
    task99()
    assert called == [99]
