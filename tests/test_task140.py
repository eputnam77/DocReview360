from docreview360.stubs.task140 import task140


def test_task140_completed(monkeypatch):
    called = False

    def fake_run():
        nonlocal called
        called = True

    monkeypatch.setattr("docreview360.stubs.task140.run", fake_run)
    task140()
    assert called
