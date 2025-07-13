from _pytest.monkeypatch import MonkeyPatch

from docreview360.monitoring import init_observability


def test_init_observability_prometheus_only() -> None:
    cfg = init_observability(port=8005, dsn=None)
    assert "prometheus" in cfg
    assert cfg["prometheus"].startswith("http://localhost:")


def test_init_observability_with_env_sentry(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("SENTRY_DSN", "http://public@localhost/1")
    cfg = init_observability(port=None)
    assert cfg["sentry"] == "enabled"
