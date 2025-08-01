from typing import Any

from docreview360.stubs.task94 import task94


def test_task94_completed(monkeypatch: Any) -> None:
    called: list[int] = []

    def record_completion(x: int) -> None:
        called.append(x)

    monkeypatch.setattr("docreview360.stubs.task94.record_task_completion", record_completion)
    task94()
    assert called == [94]
