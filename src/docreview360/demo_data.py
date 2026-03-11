# SPDX-License-Identifier: MIT
"""Demo data seeding helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from . import auth, rbac
from .approvals import approvals
from .doc_types import get_document_type, list_document_types
from .phases import list_phases
from .profile import update_preferences, update_profile_data
from .search import ProjectModel, add_project, get_project
from .workflows import create_workflow, workflow_templates

DEMO_USER_ROLES: dict[str, list[str]] = {
    "alice": ["admin", "manager", "user"],
    "bob": ["user", "reviewer"],
}

DEMO_PROFILE_DATA: dict[str, dict[str, Any]] = {
    "alice": {
        "displayName": "Alice Johnson",
        "email": "alice@example.com",
        "phone": "+1 (202) 555-0142",
        "shorthand": "AJ",
        "jobTitle": "Program Manager",
        "department": "Regulatory Affairs",
        "timeZone": "America/New_York",
        "dashboards": ["main", "admin", "user"],
        "permissions": ["admin", "manager", "user"],
        "notificationEmail": True,
        "notificationSMS": False,
        "twoFA": True,
        "theme": "dark",
    },
    "bob": {
        "displayName": "Bob Carter",
        "email": "bob@example.com",
        "phone": "+1 (415) 555-0118",
        "shorthand": "BC",
        "jobTitle": "Reviewer",
        "department": "Compliance",
        "timeZone": "America/Chicago",
        "dashboards": ["main", "user"],
        "permissions": ["user", "reviewer"],
        "notificationEmail": True,
        "notificationSMS": True,
        "twoFA": False,
        "theme": "light",
    },
}

DEMO_PROJECTS: list[dict[str, Any]] = [
    {
        "id": "demo-alice",
        "name": "Advisory Circular Updates",
        "user": "alice",
        "doc_type": "Advisory Circular",
        "document_number": "AC-2024-01",
        "description": "Review updates for the new advisory circular guidance.",
    },
    {
        "id": "demo-bob",
        "name": "Policy Memorandum Review",
        "user": "bob",
        "doc_type": "Policy Memorandum",
        "document_number": "PM-2024-07",
        "description": "Compliance review for the latest policy memorandum.",
    },
]


def _resolve_doc_type(preferred: str | None) -> tuple[str | None, list[str]]:
    doc_type = get_document_type(preferred) if preferred else None
    if doc_type is None:
        available = list_document_types()
        doc_type = available[0] if available else None
    phases = list(doc_type.phases) if doc_type and doc_type.phases else []
    if not phases:
        phases = list_phases()
    return (doc_type.name if doc_type else preferred), phases


def _resolve_workflow_template(doc_type_name: str | None) -> str:
    doc_type = get_document_type(doc_type_name) if doc_type_name else None
    template = doc_type.default_workflow_template_id if doc_type else None
    if template and template in workflow_templates:
        return template
    return "branch-coordination"


def _assign_approvals_to_user(workflow_id: str, username: str) -> None:
    if not username:
        return
    for approval in approvals.values():
        if approval.workflow == workflow_id:
            approval.reviewer = username


def seed_demo_data() -> None:
    """Ensure demo users, profiles, and projects exist when seeding is enabled."""
    if not auth._allow_demo_seed():
        return

    repo = auth._get_user_repository()
    for username, defaults in auth.DEMO_USER_DEFAULTS.items():
        record = repo.get_user(username)
        if record is None:
            repo.create_user(
                username,
                defaults["password"],
                otp_secret=defaults.get("otp_secret"),
                active=True,
            )
        elif not record.active:
            repo.set_active(username, True)

    for username, roles in DEMO_USER_ROLES.items():
        rbac.set_user_roles(username, roles, actor="system", context={"source": "demo-seed"})

    for username, data in DEMO_PROFILE_DATA.items():
        profile_updates = {k: v for k, v in data.items() if k not in {"theme", "reduce_motion"}}
        update_profile_data(username, profile_updates)
        prefs: dict[str, Any] = {}
        if "theme" in data:
            prefs["theme"] = data["theme"]
        if "reduce_motion" in data:
            prefs["reduce_motion"] = data["reduce_motion"]
        if prefs:
            update_preferences(username, prefs)

    for entry in DEMO_PROJECTS:
        project_id = entry["id"]
        if get_project(project_id):
            continue
        doc_type_name, phases = _resolve_doc_type(entry.get("doc_type"))
        template = _resolve_workflow_template(doc_type_name)
        project = ProjectModel(
            id=project_id,
            name=entry["name"],
            user=entry.get("user"),
            doc_type=doc_type_name,
            document_number=entry.get("document_number", project_id),
            description=entry.get("description"),
            updated=datetime.now(UTC),
        )
        if phases:
            workflow = create_workflow(project.id, phases, template=template)
            project.workflow = workflow.id
            project.initial_phase = workflow.phase
            _assign_approvals_to_user(workflow.id, project.user or "")
        add_project(project)
