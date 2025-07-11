import httpx

from docreview360.stubs.task30 import fetch_length_task, task30


def test_task30_word_count() -> None:
    assert task30("hello world") == 2


def test_task30_fetch_length(monkeypatch) -> None:
    def fake_get(url: str, timeout: int = 5):
        class Resp:
            text = "ok"

            def raise_for_status(self) -> None:  # pragma: no cover - not used
                pass

        assert url == "http://example.com"
        return Resp()

    monkeypatch.setattr(httpx, "get", fake_get)
    assert fetch_length_task("http://example.com") == 2
