"""Integration tests for the Documenso signature connector."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import httpx
import pytest
from docreview360 import provider_store
from docreview360.integrations.signature import documenso
from docreview360.monitoring import SIGNATURE_FAILURES


@pytest.fixture(autouse=True)
def reset_documenso_state() -> None:
    documenso._signatures.clear()
    documenso._sig_workflows.clear()
    documenso._sig_certificates.clear()
    documenso._certificates.clear()
    documenso._reset_circuit_breaker_for_tests()
    yield
    documenso._signatures.clear()
    documenso._sig_workflows.clear()
    documenso._sig_certificates.clear()
    documenso._certificates.clear()
    documenso._reset_circuit_breaker_for_tests()


def test_complete_signature_records_metric(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP failures increment metrics with the failure reason."""

    monkeypatch.setattr(documenso, "DOCUMENSO_URL", "https://remote")
    monkeypatch.setattr(documenso, "FAILURE_THRESHOLD", 5)
    monkeypatch.setattr(documenso, "log_event", lambda *args, **kwargs: None)

    reason = "complete_signature:ConnectError"

    def failing_post(url: str, **_kwargs: object) -> httpx.Response:
        request = httpx.Request("POST", url)
        raise httpx.ConnectError("boom", request=request)

    monkeypatch.setattr(documenso, "http_post", failing_post)

    with pytest.raises(RuntimeError):
        documenso.complete_signature("sig-1")

    metric = SIGNATURE_FAILURES.labels("documenso", reason)
    assert metric._value.get() == 1
    SIGNATURE_FAILURES.remove("documenso", reason)


def test_circuit_breaker_switches_to_stub(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Repeated failures trigger the breaker and persist provider health."""

    providers_file = tmp_path / "providers.yaml"
    monkeypatch.setattr(provider_store, "PROVIDERS_FILE", providers_file)

    monkeypatch.setattr(documenso, "DOCUMENSO_URL", "https://remote")
    monkeypatch.setattr(documenso, "FAILURE_THRESHOLD", 2)
    monkeypatch.setattr(documenso, "FAILURE_WINDOW_SECONDS", 60)
    monkeypatch.setattr(documenso, "FAILURE_COOLDOWN_SECONDS", 1)
    monkeypatch.setattr(documenso, "log_event", lambda *args, **kwargs: None)

    reason = "complete_signature:ConnectError"

    def failing_post(url: str, **_kwargs: object) -> httpx.Response:
        request = httpx.Request("POST", url)
        raise httpx.ConnectError("boom", request=request)

    monkeypatch.setattr(documenso, "http_post", failing_post)

    with pytest.raises(RuntimeError):
        documenso.complete_signature("sig-a")
    assert documenso._remote_suspended_until is None

    documenso.complete_signature("sig-b")
    assert documenso._signatures["sig-b"] == "signed"
    assert documenso._remote_suspended_until is not None

    metric = SIGNATURE_FAILURES.labels("documenso", reason)
    assert metric._value.get() == 2
    SIGNATURE_FAILURES.remove("documenso", reason)

    providers = provider_store.load_providers(providers_file)
    assert providers["documenso"]["healthy"] is False

    def forbid_remote(
        *_args: object, **_kwargs: object
    ) -> httpx.Response:  # pragma: no cover - safety
        raise AssertionError("remote call invoked during suspension")

    monkeypatch.setattr(documenso, "http_post", forbid_remote)
    sig_id, url, _meta = documenso.request_signature("doc-1", "alice")
    assert sig_id in documenso._signatures and url.endswith(sig_id)

    documenso._remote_suspended_until = documenso._now() - timedelta(seconds=1)

    def healthy_get(url: str, **_kwargs: object) -> httpx.Response:
        request = httpx.Request("GET", url)
        return httpx.Response(200, request=request)

    monkeypatch.setattr(documenso, "http_get", healthy_get)

    assert documenso.health_check() is True
    providers = provider_store.load_providers(providers_file)
    assert providers["documenso"]["healthy"] is True
