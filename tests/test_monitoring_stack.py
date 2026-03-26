from __future__ import annotations

import pytest
from docreview360.monitoring import start_observability_stack


def test_start_observability_stack_handles_optional_sentry(monkeypatch) -> None:
    """Sentry should only be reported when a DSN is configured."""
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    cfg = start_observability_stack(8003, 3003)
    assert "sentry" not in cfg

    monkeypatch.setenv("SENTRY_DSN", "http://public@localhost/1")
    cfg = start_observability_stack(8004, 3004)
    assert cfg["sentry"] == "enabled"


def test_start_observability_stack_rejects_bool_grafana_port() -> None:
    with pytest.raises(TypeError):
        start_observability_stack(8000, True)
