from docreview360.approvals import approvals, create_approval, send_for_signature
from docreview360.audit import clear_audit_log, get_audit_log
from docreview360.documents import documents, import_document
from docreview360.logs import clear_logs


def test_linkage_changes_are_audited() -> None:
    approvals.clear()
    documents.clear()
    clear_logs()
    clear_audit_log()

    doc1 = import_document("d1.md", b"doc1")
    approval = create_approval(
        "wf", "user", doc1.id, document=b"doc1", signature_provider="documenso"
    )

    log_entries_doc1 = get_audit_log(doc1.id)
    assert any(
        ev.action == "approval_linked" and ev.context.get("approval_id") == approval.id
        for ev in log_entries_doc1
    )
    assert approval.id in documents[doc1.id].approval_ids

    doc2 = import_document("d2.md", b"doc2")
    send_for_signature(approval.id, doc2.id, user="user")

    assert approval.id not in documents[doc1.id].approval_ids
    assert approval.id in documents[doc2.id].approval_ids

    log_entries_old = get_audit_log(doc1.id)
    assert any(
        ev.action == "approval_unlinked" and ev.context.get("approval_id") == approval.id
        for ev in log_entries_old
    )

    log_entries_new = get_audit_log(doc2.id)
    assert any(
        ev.action == "approval_linked" and ev.context.get("approval_id") == approval.id
        for ev in log_entries_new
    )
