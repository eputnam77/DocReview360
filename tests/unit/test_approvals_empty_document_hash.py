import hashlib

from docreview360.approvals import approvals, create_approval


def test_create_approval_hashes_empty_document() -> None:
    """Empty documents should still record a deterministic hash."""

    approvals.clear()
    approval = create_approval("wf", "reviewer", doc_id="doc", document=b"")

    try:
        assert approval.document_hash == hashlib.sha256(b"").hexdigest()
    finally:
        approvals.pop(approval.id, None)
