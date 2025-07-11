"""Implementation for task 41."""

from ..documents import (
    get_document_versions,
    import_document,
    update_document,
)
from . import record_task_completion


def task41() -> list[str]:
    """Return versions after a couple of edits."""
    doc = import_document("stub.md", b"one")
    update_document(doc.id, "two")
    update_document(doc.id, "three")
    versions = get_document_versions(doc.id)
    # cleanup to avoid polluting other tests
    from .. import documents as _docs

    del _docs.documents[doc.id]
    record_task_completion(41)
    return versions
