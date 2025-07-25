from docreview360.stubs.task95 import task95


def test_task95_completed(monkeypatch):
    called: list[int] = []
    monkeypatch.setattr(
        "docreview360.stubs.task95.record_task_completion", lambda x: called.append(x)
    )
    task95()
    assert called == [95]
