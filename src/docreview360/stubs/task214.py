"""Link a template to a document type."""

from __future__ import annotations

from ..doc_types import DocumentTypeModel
from . import record_task_completion


def task214(doc_type: DocumentTypeModel, template_id: str) -> DocumentTypeModel:
    """Set ``template_id`` as the default for ``doc_type`` and return it."""

    if not template_id:
        raise ValueError("template_id required")

    record_task_completion(214)
    doc_type.default_template_id = template_id
    return doc_type
