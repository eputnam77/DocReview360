
from docreview360 import doc_types, email_templates, template_manager
from docreview360.api import _seed_default_document_templates, _seed_default_email_templates


def test_default_document_templates_seeded(tmp_path) -> None:
    template_manager.reset_template_store(root=tmp_path / "template_store.json")
    _seed_default_document_templates()
    templates = template_manager.list_stored_templates()
    doc_type_names = [dt.name for dt in doc_types.list_document_types()]
    assert doc_type_names, "Expected default document types to exist"
    for name in doc_type_names:
        template_id = f"doc_type::{name}"
        assert template_id in templates
        metadata = templates[template_id].metadata
        assert metadata.get("docType") == name
        assert metadata.get("default") is True


def test_default_email_templates_seeded(tmp_path) -> None:
    email_templates.reset_email_templates(root=tmp_path / "email_templates.json")
    _seed_default_email_templates()
    names = {t.name for t in email_templates.list_templates()}
    assert {"default", "review_request", "approval_request", "signature_request", "comment_added", "project_assigned", "phase_changed", "due_reminder", "overdue_notice", "completion_notice", "review_complete", "approval_complete"}.issubset(names)
