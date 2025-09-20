import pytest

from docreview360 import monitoring


def test_init_observability_handles_legacy_start_http_server(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    def fake_start_http_server(port: int):
        calls.append(port)
        if len(calls) == 1:
            raise OSError("address in use")
        return None  # older prometheus_client versions return ``None``

    monkeypatch.setattr(monitoring, "start_http_server", fake_start_http_server)

    services = monitoring.init_observability(8001)

    assert calls[0] == 8001
    assert len(calls) == 2  # second attempt should pick a different port
    fallback_port = calls[1]
    assert fallback_port != 8001
    assert services["prometheus"] == f"http://localhost:{fallback_port}/"
