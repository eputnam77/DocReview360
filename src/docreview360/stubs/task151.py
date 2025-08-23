"""Admin-less project creation wizard helper (Task 151)."""

from __future__ import annotations

from typing import Iterable
from uuid import uuid4

from ..doc_types import (
    DEFAULT_DOC_TYPE_NAMES,
    DEFAULT_DOC_TYPE_PHASES,
    DocumentTypeModel,
    document_types,
    get_document_type,
)
from ..project_init import create_project_with_validation
from ..workflows import get_workflow
from . import record_task_completion


def task151(doc_type: str | None = None, reviewers: Iterable[str] | None = None) -> tuple[str, str]:
    """Create a project without admin privileges.

    Parameters
    ----------
    doc_type:
        Name of the document type to base the project on. Must exist.
    reviewers:
        Optional list of reviewers to assign to the initial workflow.

    Returns
    -------
    tuple[str, str]
        ``(project_id, workflow_id)`` of the created objects.
    """

    if doc_type is None:
        doc_type = DEFAULT_DOC_TYPE_NAMES[0]
    dt = get_document_type(doc_type)
    if dt is None and doc_type in DEFAULT_DOC_TYPE_NAMES:
        document_types[doc_type] = DocumentTypeModel(
            name=doc_type,
            template=f"<h1>{doc_type}</h1>",
            workflow=DEFAULT_DOC_TYPE_PHASES[doc_type],
        )
        dt = document_types[doc_type]
    if dt is None:
        raise ValueError(f"unknown document type {doc_type}")

    project_id = uuid4().hex
    project, wf_id = create_project_with_validation(
        project_id,
        f"{doc_type}-project",
        dt.template,
        reviewers or [],
    )

    # Ensure workflow exists to mirror UI behaviour
    if get_workflow(wf_id) is None:
        raise RuntimeError("workflow creation failed")

    record_task_completion(151)
    return project.id, wf_id
