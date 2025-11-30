# ruff: noqa: E402, I001
from pathlib import Path

import os
import pytest
import docreview360.database as db_mod

os.environ.setdefault("DOCREVIEW360_DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture(autouse=True)
def _no_db_migrations(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid running heavy DB migrations during these tests."""

    monkeypatch.setattr(db_mod.Database, "migrate", lambda self, *a, **k: None)


import docreview360.logs as logs_mod
import docreview360.audit as audit_mod
from docreview360 import provider_store
from docreview360.approvals import approvals, create_approval, send_for_signature
from docreview360.documents import DocumentModel, documents
from docreview360.integrations.signature import base


class FailingProvider:
    name = "fail"

    def request_signature(self, *args, **kwargs):
        raise RuntimeError("boom")

    def process_webhook(self, data):  # pragma: no cover - stub
        pass

    def verify_signature(self, signature_id, document):  # pragma: no cover - stub
        return False

    def validate_signature(
        self, document_bytes, certificate_url, metadata
    ):  # pragma: no cover - stub
        return False

    def health_check(self) -> bool:  # pragma: no cover - stub
        return False


class OkProvider:
    name = "ok"

    def request_signature(self, *args, **kwargs):
        return "sig", "url", {}

    def process_webhook(self, data):  # pragma: no cover - stub
        pass

    def verify_signature(self, signature_id, document):  # pragma: no cover - stub
        return True

    def validate_signature(
        self, document_bytes, certificate_url, metadata
    ):  # pragma: no cover - stub
        return True

    def health_check(self) -> bool:  # pragma: no cover - stub
        return True


def test_send_for_signature_failover(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(logs_mod, "log_event", lambda *a, **k: None)
    monkeypatch.setattr(audit_mod, "log_audit_event", lambda *a, **k: None)
    path = tmp_path / "providers.yaml"
    monkeypatch.setattr(provider_store, "PROVIDERS_FILE", path)
    monkeypatch.setattr(provider_store, "DEFAULT_PROVIDERS", {})
    provider_store.save_providers(
        {
            "fail": {"api_key": "", "priority": 1, "healthy": True},
            "ok": {"api_key": "", "priority": 2, "healthy": True},
        },
        path,
    )
    base.providers.clear()
    base.register_provider(FailingProvider())
    base.register_provider(OkProvider())

    doc_id = "doc1"
    documents[doc_id] = DocumentModel(id=doc_id, content="hello")
    appr = create_approval("wf1", "alice", doc_id, document=b"hello")
    url = send_for_signature(appr.id, doc_id, "alice")
    assert url == "url"
    assert approvals[appr.id].signature_provider == "ok"
    data = provider_store.load_providers(path)
    assert data["fail"]["healthy"] is False


def test_default_provider_prefers_sandbox(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reload signature module with a clean env and prefer sandbox provider."""

    for env_var in (
        "SIGNATURE_PROVIDER",
        "SIGNATURE_PROVIDER_PRIMARY",
        "SIGNATURE_PROVIDER_FALLBACK",
    ):
        monkeypatch.delenv(env_var, raising=False)

    import importlib

    importlib.reload(base)

    assert base.get_default_provider() == "sandbox"
