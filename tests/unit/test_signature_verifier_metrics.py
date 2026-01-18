import hashlib
from datetime import datetime, timezone

import pytest

import services.signature_verifier as signature_verifier
from docreview360.approvals import ApprovalModel, approvals
from docreview360.documents import DocumentModel, documents
from docreview360.monitoring import VERIFICATION_COUNTER


def _counter_value(source: str, status: str) -> float:
    for metric in VERIFICATION_COUNTER.collect():
        for sample in metric.samples:
            if sample.labels.get("source") == source and sample.labels.get("status") == status:
                return float(sample.value)
    return 0.0


class FailingProvider:
    name = "failing"

    def validate_signature(
        self, document_bytes: bytes, certificate_url: str | None, metadata: dict
    ) -> bool:
        return False


def test_verify_document_signatures_records_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(signature_verifier, "get_provider", lambda name: FailingProvider())

    doc = DocumentModel(id="doc-metrics", content="document body")
    doc.date = datetime.now(timezone.utc)
    documents[doc.id] = doc

    document_hash = hashlib.sha256(doc.content.encode("utf-8")).hexdigest()
    approval = ApprovalModel(
        id="approval-metrics",
        workflow="wf",
        reviewer="alice",
        document_id=doc.id,
        signature_provider="failing",
        document_hash=document_hash,
        certificate_url="https://example.test/cert",
        state="approved",
    )
    approvals[approval.id] = approval

    before_failure = _counter_value("background", "failure")
    before_success = _counter_value("background", "success")

    try:
        processed = signature_verifier.verify_document_signatures(
            scope="approved", document_ids=[doc.id], username="system"
        )
        assert processed == 1
        assert _counter_value("background", "failure") == before_failure + 1
        assert _counter_value("background", "success") == before_success
    finally:
        approvals.pop(approval.id, None)
        documents.pop(doc.id, None)
