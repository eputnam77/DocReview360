"""Auto-apply a document template when creating a project."""

from __future__ import annotations

from ..doc_types import DocumentTypeModel
from ..documents import DocumentModel
from ..search import ProjectModel
from ..stubs import record_task_completion
from ..template_manager import get_latest_template


def task215(project: ProjectModel, doc_type: DocumentTypeModel) -> DocumentModel:
    """Return a new document populated with the latest template."""

    if not project.id:
        raise ValueError("project id required")

    record_task_completion(215)
    content = doc_type.template
    if doc_type.default_template_id:
        latest = get_latest_template(doc_type.default_template_id)
        if latest:
            content = latest.content.decode()
    return DocumentModel(
        id="init-" + project.id,
        content=content,
        project=project.id,
        user=project.user,
    )
