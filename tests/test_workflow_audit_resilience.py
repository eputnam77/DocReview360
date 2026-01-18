from docreview360.approvals import approvals
from docreview360.audit import clear_audit_log, get_audit_log
from docreview360.documents import documents
from docreview360.logs import clear_logs
from docreview360.workflows import create_workflow, start_workflow, workflows


def test_start_workflow_still_logs_audit_when_patched(monkeypatch):
    approvals.clear()
    workflows.clear()
    documents.clear()
    clear_logs()
    clear_audit_log()
    wf = create_workflow("proj", ["draft"])
    clear_logs()
    clear_audit_log()
    # Patch log_audit_event to a stub that drops events
    monkeypatch.setattr("docreview360.audit.log_audit_event", lambda *a, **k: None)
    start_workflow(wf.id, "Doc", b"content")
    doc_id = workflows[wf.id].document
    entries = get_audit_log(doc_id)
    assert any(e.event == "approval_doc_linked" for e in entries)
