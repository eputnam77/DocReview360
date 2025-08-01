from typing import Any

from docreview360.stubs.task93 import task93


def test_task93_completed(monkeypatch: Any) -> None:
    calls: list[int] = []

    def record_completion(x: int) -> None:
        calls.append(x)

    monkeypatch.setattr("docreview360.stubs.task93.record_task_completion", record_completion)
    task93()
    assert calls == [93]
