from docreview360.stubs.task138 import task138


def test_task138_completed(monkeypatch):
    called = {}

    def fake_generate(out):
        called["out"] = out

    monkeypatch.setattr("docreview360.stubs.task138.generate", fake_generate)
    task138("out")
    assert called["out"] == "out"
