from typing import Any

from docreview360.stubs.task95 import task95


def test_task95_completed(monkeypatch: Any) -> None:
    called: list[int] = []

    def record_completion(x: int) -> None:
        called.append(x)

    monkeypatch.setattr("docreview360.stubs.task95.record_task_completion", record_completion)
    task95()
    assert called == [95]
