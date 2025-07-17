"""Auto-apply a document template when creating a project."""

from __future__ import annotations

from ..doc_types import DocumentTypeModel
from ..documents import DocumentModel
from ..search import ProjectModel
from ..stubs import record_task_completion


def task215(project: ProjectModel, doc_type: DocumentTypeModel) -> DocumentModel:
    """Return a new document populated with ``doc_type.template``."""

    if not project.id:
        raise ValueError("project id required")

    record_task_completion(215)
    return DocumentModel(
        id="init-" + project.id,
        content=doc_type.template,
        project=project.id,
        user=project.user,
    )
