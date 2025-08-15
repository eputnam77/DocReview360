from docreview360.approvals import approvals
from docreview360.audit import clear_audit_log, get_audit_log
from docreview360.documents import documents
from docreview360.logs import clear_logs, logs
from docreview360.workflows import create_workflow, start_workflow, workflows


def test_start_workflow_links_approvals_and_logs_doc_id() -> None:
    approvals.clear()
    workflows.clear()
    documents.clear()
    clear_logs()
    clear_audit_log()

    wf = create_workflow("proj", ["draft"])
    approval_ids = [a.id for a in approvals.values() if a.workflow == wf.id]
    assert approval_ids
    assert all(approvals[a_id].document_id == wf.id for a_id in approval_ids)

    clear_logs()
    clear_audit_log()

    start_workflow(wf.id, "MyDoc", b"content")
    doc_id = workflows[wf.id].document
    assert doc_id is not None
    assert all(approvals[a_id].document_id == doc_id for a_id in approval_ids)

    log_entries = [e for e in logs if e.action == "approval_doc_linked"]
    assert log_entries
    assert all(entry.context.get("doc_id") == doc_id for entry in log_entries)

    audit_entries = get_audit_log(doc_id)
    assert any(ev.action == "approval_doc_linked" for ev in audit_entries)
