from docreview360.stubs.task93 import task93


def test_task93_completed(monkeypatch):
    calls: list[int] = []
    monkeypatch.setattr(
        "docreview360.stubs.task93.record_task_completion", lambda x: calls.append(x)
    )
    task93()
    assert calls == [93]
