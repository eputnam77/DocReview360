from docreview360.stubs.task94 import task94


def test_task94_completed(monkeypatch):
    called: list[int] = []
    monkeypatch.setattr(
        "docreview360.stubs.task94.record_task_completion", lambda x: called.append(x)
    )
    task94()
    assert called == [94]
