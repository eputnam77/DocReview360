# SPDX-License-Identifier: MIT
"""Deterministic E2E data seeding helpers."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse

from . import auth, comments, rbac, reviews
from .approvals import approvals, reset_approvals
from .doc_types import DocumentTypeModel, add_document_type, reset_document_types
from .documents import DocumentModel, documents
from .phases import add_phase, reset_phases
from .search import ProjectModel, _reset_state_for_testing, add_project
from .template_manager import reset_template_store
from .workflows import create_workflow, reset_workflow_templates

E2E_SEED_USERS = {
    "alice": {"password": "password", "roles": ["reviewer", "user"]},
    "bob": {"password": "password", "roles": ["admin", "user"]},
}

E2E_DOC_TYPE = "E2E Test Document Type"
E2E_DOC_TYPES = [
    "Advisory Circular",
    "Policy Statement",
    "Release Notes",
    E2E_DOC_TYPE,
]
E2E_PHASES = ["draft", "review", "approval"]
E2E_PROJECT_ID = "e2e-project-001"


def _sqlite_path_from_url(url: str | None) -> Path | None:
    if not url:
        return None
    parsed = urlparse(url)
    if not parsed.scheme.startswith("sqlite"):
        return None
    if parsed.path:
        return Path(parsed.path)
    return None


def _unlink_if_exists(path: Path | None) -> None:
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def reset_e2e_state() -> None:
    """Clear persisted and in-memory state for a clean E2E run."""

    _unlink_if_exists(_sqlite_path_from_url(os.getenv("DOCREVIEW360_DATABASE_URL")))
    _unlink_if_exists(
        Path(os.getenv("DOCREVIEW360_USER_DB", ""))
        if os.getenv("DOCREVIEW360_USER_DB")
        else None
    )
    _unlink_if_exists(
        Path(os.getenv("DOCREVIEW360_RBAC_DB", ""))
        if os.getenv("DOCREVIEW360_RBAC_DB")
        else None
    )
    _unlink_if_exists(
        Path(os.getenv("DOCREVIEW360_SEARCH_DB", ""))
        if os.getenv("DOCREVIEW360_SEARCH_DB")
        else None
    )

    reset_template_store()
    reset_document_types()
    reset_phases()
    reset_workflow_templates()
    reviews.reset_reviews()
    comments.reset_comment_state()
    documents.clear()
    reset_approvals()

    search_db = os.getenv("DOCREVIEW360_SEARCH_DB")
    _reset_state_for_testing(db_path=search_db)
    rbac.reset_role_assignments(
        include_defaults=True,
        actor="e2e",
        context={"source": "e2e-seed"},
    )

    # Reset user repository if the DB path moved.
    if os.getenv("DOCREVIEW360_USER_DB"):
        auth.configure_user_repository(os.getenv("DOCREVIEW360_USER_DB"))


def seed_e2e_data() -> Dict[str, Any]:
    """Seed deterministic data for E2E tests and return a summary payload."""

    reset_e2e_state()

    repo = auth._get_user_repository()
    for username, info in E2E_SEED_USERS.items():
        record = repo.get_user(username)
        if record is None:
            repo.create_user(username, info["password"], otp_secret="123456", active=True)
        elif not record.active:
            repo.set_active(username, True)
        rbac.set_user_roles(
            username,
            info["roles"],
            actor="e2e",
            context={"source": "e2e-seed"},
        )

    for phase in E2E_PHASES:
        add_phase(phase)

    for doc_type_name in E2E_DOC_TYPES:
        doc_type = DocumentTypeModel(
            name=doc_type_name,
            template=f"<h1>{doc_type_name} Template</h1>",
            workflow=E2E_PHASES,
            default_template_id="branch-coordination",
        )
        add_document_type(doc_type)

    project = ProjectModel(
        id=E2E_PROJECT_ID,
        name="E2E Document Review",
        user="bob",
        doc_type=E2E_DOC_TYPES[0],
        document_number="DOC-001",
        description="Seeded project for E2E tests.",
        updated=datetime.now(UTC),
    )
    workflow = create_workflow(project.id, E2E_PHASES)
    project.workflow = workflow.id
    project.initial_phase = workflow.phase
    add_project(project)

    # Seed a placeholder document to keep document-related views consistent.
    documents[project.id] = DocumentModel(
        id=project.id,
        content="Seeded document content.",
        project=project.id,
        user="bob",
        date=datetime.now(UTC),
    )

    # Mark approvals for the initial phase as approved so phase advancement is unblocked.
    for approval in approvals.values():
        if approval.workflow == workflow.id and approval.phase_id == workflow.phase:
            approval.state = "approved"
            approval.signed_at = datetime.now(UTC)

    return {
        "users": {name: {"roles": info["roles"]} for name, info in E2E_SEED_USERS.items()},
        "doc_types": list(E2E_DOC_TYPES),
        "project": {
            "id": project.id,
            "name": project.name,
            "workflow_id": workflow.id,
            "phase": workflow.phase,
            "doc_type": project.doc_type,
        },
        "phases": list(E2E_PHASES),
    }
