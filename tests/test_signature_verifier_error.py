import hashlib

from docreview360.approvals import ApprovalModel, approvals
from docreview360.audit import clear_audit_log, get_audit_log
from docreview360.documents import import_document

from services import signature_verifier


class RaisingProvider:
    def validate_signature(self, *args, **kwargs):
        raise RuntimeError("boom")


def test_verify_document_signatures_handles_provider_errors(monkeypatch) -> None:
    approvals.clear()
    clear_audit_log()
    doc = import_document("doc.txt", b"hello")
    approvals["a1"] = ApprovalModel(
        id="a1",
        workflow="wf",
        reviewer="alice",
        document_id=doc.id,
        state="approved",
        signature_provider="raising",
        signature_id="s1",
        document_hash=hashlib.sha256(b"hello").hexdigest(),
        certificate_url="url",
        provider_metadata={},
    )

    monkeypatch.setattr(signature_verifier, "get_provider", lambda name: RaisingProvider())

    processed = signature_verifier.verify_document_signatures.run()  # type: ignore[attr-defined]
    assert processed == 1
    events = get_audit_log(doc.id)
    assert events[-1].context["signature_valid"] is False

