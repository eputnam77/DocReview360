from docreview360.stubs.task98 import task98


def test_task98_completed(monkeypatch):
    called: list[int] = []
    monkeypatch.setattr(
        "docreview360.stubs.task98.record_task_completion", lambda x: called.append(x)
    )
    task98()
    assert called == [98]
