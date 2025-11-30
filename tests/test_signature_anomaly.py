"""Tests for signature anomaly handling using stubbed providers."""

# ruff: noqa: E402

import hashlib
import sys
import types
from typing import Any, Dict

import pytest


def _approval_likelihood_stub(
    text: str, critic: object | None = None, *, doc_type: str | None = None
) -> float:
    return 1.0


quality_stub = types.ModuleType("docreview360.quality")
quality_stub.approval_likelihood = _approval_likelihood_stub
sys.modules.setdefault("docreview360.quality", quality_stub)

torch_models_stub = types.ModuleType("docreview360.ml.torch_models")


class _TinyCritic:  # pragma: no cover - stub for imports
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass


def _update_critic_stub(*args: Any, **kwargs: Any) -> None:
    return None


torch_models_stub.TinyCritic = _TinyCritic
torch_models_stub.update_critic = _update_critic_stub
sys.modules.setdefault("docreview360.ml.torch_models", torch_models_stub)

api_stub = types.ModuleType("docreview360.api")
api_stub.__path__ = []  # type: ignore[attr-defined]
webhooks_stub = types.ModuleType("docreview360.api.webhooks")
webhooks_stub.emit_verification_completed = lambda *args: None
sys.modules.setdefault("docreview360.api", api_stub)
sys.modules.setdefault("docreview360.api.webhooks", webhooks_stub)


from docreview360.approvals import ApprovalModel, approvals, verify_document_signature
from docreview360.audit import get_audit_log
from docreview360.documents import DocumentModel, documents
from docreview360.integrations import registry
from docreview360.integrations.signature import base as signature_base
from docreview360.monitoring import SIGNATURE_ANOMALIES


class StubSignatureProvider:
    name = "stub-anomaly"

    def request_signature(
        self, *args: Any, **kwargs: Any
    ) -> tuple[str, str, Dict[str, Any]]:  # pragma: no cover - not used
        raise NotImplementedError

    def process_webhook(self, data: Dict[str, Any]) -> None:  # pragma: no cover - not used
        pass

    def verify_signature(
        self, signature_id: str, document: bytes
    ) -> bool:  # pragma: no cover - not used
        return False

    def validate_signature(
        self, document_bytes: bytes, certificate_url: str | None, metadata: Dict[str, Any]
    ) -> bool:
        return False

    def health_check(self) -> bool:  # pragma: no cover - not used
        return True


def _metric_value(label: str) -> float:
    sample = SIGNATURE_ANOMALIES.labels(label)
    value = getattr(sample, "_value", None)
    if value is None:
        return 0.0
    return float(value.get())


def test_signature_anomaly_triggers_escalation(monkeypatch: pytest.MonkeyPatch) -> None:
    approvals.clear()
    documents.clear()

    monkeypatch.setattr(signature_base, "providers", {})
    monkeypatch.setattr(registry, "_providers", {})
    provider = StubSignatureProvider()
    signature_base.register_provider(provider)
    monkeypatch.setattr(
        "docreview360.integrations.signature.base.get_default_providers",
        lambda: [provider.name],
    )

    doc_id = "doc-anomaly"
    content = "suspicious contract"
    documents[doc_id] = DocumentModel(id=doc_id, content=content, history=[])
    approval = ApprovalModel(
        id="approval-anomaly",
        workflow="wf",
        reviewer="alice",
        document_id=doc_id,
        state="approved",
        signature_provider=provider.name,
        signature_id="sig-123",
        document_hash=hashlib.sha256(content.encode()).hexdigest(),
        certificate_url=None,
        provider_metadata={"certificate_chain": []},
        escalate_to="security-team",
        delegates=[],
    )
    approvals[approval.id] = approval

    before = _metric_value("escalated")
    result = verify_document_signature(doc_id)
    detail = next(d for d in result["details"] if d["approval_id"] == approval.id)

    assert detail["anomaly_escalated"] is True
    assert detail["escalation_target"] == "security-team"
    assert detail["anomaly_score"] >= detail["anomaly_threshold"]

    after = _metric_value("escalated")
    assert after == pytest.approx(before + 1)

    audit_entries = get_audit_log(doc_id)
    anomaly_entries = [entry for entry in audit_entries if entry.event == "signature_anomaly"]
    assert anomaly_entries, "expected anomaly audit entry"
    entry = anomaly_entries[-1]
    assert entry.status == "escalated"
    assert entry.context.get("model_hash")
    assert entry.context.get("model_version") == "1.0.0"
    assert entry.context.get("target") == "security-team"
