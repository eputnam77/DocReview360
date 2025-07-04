"""Trigger re-review when document edits are substantial."""

from ..documents import needs_rereview, update_document
from . import record_task_completion


def task49(doc_id: str, new_content: str) -> bool:
    """Update the document and return whether re-review is needed."""
    update_document(doc_id, new_content)
    record_task_completion(49)
    return needs_rereview(doc_id)
