import socket

import pytest
from _pytest.monkeypatch import MonkeyPatch
from docreview360.monitoring import init_observability


def test_init_observability_prometheus_only() -> None:
    cfg = init_observability(port=0, dsn=None)
    assert "prometheus" in cfg
    assert cfg["prometheus"].startswith("http://localhost:")


def test_init_observability_port_in_use() -> None:
    """If the desired port is busy an ephemeral one should be used."""
    sock = socket.socket()
    sock.bind(("", 0))
    port = sock.getsockname()[1]
    try:
        cfg = init_observability(port=port, dsn=None)
    finally:
        sock.close()
    assert cfg["prometheus"].startswith("http://localhost:")
    assert not cfg["prometheus"].startswith(f"http://localhost:{port}")


def test_init_observability_with_env_sentry(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("SENTRY_DSN", "http://public@localhost/1")
    cfg = init_observability(port=None)
    assert cfg["sentry"] == "enabled"


def test_init_observability_rejects_bool_port() -> None:
    with pytest.raises(TypeError):
        init_observability(port=True, dsn=None)
