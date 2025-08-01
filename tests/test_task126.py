import pytest
from docreview360.stubs.task126 import task126


def test_task126_completed(monkeypatch: pytest.MonkeyPatch) -> None:
    def dummy_sync(url: str, token: str) -> None:
        assert url == "https://mb.example"
        assert token == "tkn"

    monkeypatch.setattr("docreview360.stubs.task126.run_field_sync", dummy_sync)
    task126("https://mb.example", "tkn")
