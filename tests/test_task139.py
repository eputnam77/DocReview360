from docuflow.stubs.task139 import task139


def test_task139_completed(monkeypatch):
    class Dummy:
        def is_enabled(self, name, context=None):
            return True

    monkeypatch.setattr("docuflow.stubs.task139.FeatureFlags", lambda url, api_key: Dummy())
    assert task139("http://example", "key", "flag")
