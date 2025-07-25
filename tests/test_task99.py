from docreview360.stubs.task99 import task99


def test_task99_completed(monkeypatch):
    called: list[int] = []
    monkeypatch.setattr(
        "docreview360.stubs.task99.record_task_completion", lambda x: called.append(x)
    )
    task99()
    assert called == [99]
