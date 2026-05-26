# SPDX-License-Identifier: MIT
"""Workflow template management — CRUD, defaults, DB persistence."""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
from datetime import datetime, timezone
from typing import Dict, List

from ._models import (
    ApprovalStep,
    WorkflowTemplateModel,
    WorkflowTemplatePayload,
    WorkflowTemplateStep,
)

_logger = logging.getLogger(__name__)

# Package-level store references (shared across reloads via the package object)
_pkg = sys.modules.get(__name__.rpartition(".")[0])
if _pkg is not None and hasattr(_pkg, "_workflow_template_definitions_store"):
    workflow_template_definitions = getattr(_pkg, "_workflow_template_definitions_store")
else:
    workflow_template_definitions: Dict[str, WorkflowTemplateModel] = {}
    if _pkg is not None:
        setattr(_pkg, "_workflow_template_definitions_store", workflow_template_definitions)

if _pkg is not None and hasattr(_pkg, "_workflow_templates_store"):
    workflow_templates = getattr(_pkg, "_workflow_templates_store")  # type: ignore[assignment]
else:
    workflow_templates: Dict[str, List[ApprovalStep]] = {}
    if _pkg is not None:
        setattr(_pkg, "_workflow_templates_store", workflow_templates)

_TEMPLATES_LOADED: bool = False
_TEMPLATES_LOAD_LOCK = threading.Lock()


def _env_flag_enabled(value: str | None) -> bool:
    """Interpret truthy string values for the persistence feature flag."""
    if value is None:
        return True
    normalized = value.strip().lower()
    return normalized not in {"0", "false", "no", "off"}


DOCREVIEW360_ENABLE_WORKFLOW_TEMPLATE_PERSISTENCE = _env_flag_enabled(
    os.getenv("DOCREVIEW360_ENABLE_WORKFLOW_TEMPLATE_PERSISTENCE")
)

DEFAULT_WORKFLOW_TEMPLATES: Dict[str, List[ApprovalStep]] = {
    # ---- Primary government document review workflows ----
    "standard-review": [
        ApprovalStep(
            role="Author / Program Analyst",
            description="Drafts the document and performs initial self-review",
            order=1,
        ),
        ApprovalStep(
            role="Subject Matter Expert",
            description="Reviews for technical accuracy and completeness",
            order=2,
        ),
        ApprovalStep(
            role="Legal / Policy Counsel",
            description="Reviews for regulatory compliance and legal sufficiency",
            order=3,
        ),
        ApprovalStep(
            role="Division Director",
            description="Management endorsement before final signature",
            order=4,
        ),
        ApprovalStep(
            role="Approving Official",
            description="Final signature authority and publication approval",
            order=5,
        ),
    ],
    "fast-track": [
        ApprovalStep(
            role="Author",
            description="Drafts the document with urgency notation",
            order=1,
        ),
        ApprovalStep(
            role="Approving Official",
            description="Expedited final approval with documented justification",
            order=2,
        ),
    ],
    "sop-review": [
        ApprovalStep(
            role="Process Owner",
            description="Drafts the procedure and verifies operational accuracy",
            order=1,
        ),
        ApprovalStep(
            role="Peer Reviewer",
            description="Reviews for technical soundness and practicality",
            order=2,
        ),
        ApprovalStep(
            role="Supervisor / Branch Chief",
            description="Operational review and unit-level approval",
            order=3,
        ),
        ApprovalStep(
            role="Approving Official",
            description="Final approval and effective-date assignment",
            order=4,
        ),
    ],
    "inter-agency-coordination": [
        ApprovalStep(
            role="Lead Author",
            description="Drafts the document and coordinates internal review",
            order=1,
        ),
        ApprovalStep(
            role="Internal Legal / Policy Reviewer",
            description="Reviews for internal regulatory compliance",
            order=2,
        ),
        ApprovalStep(
            role="External Agency Liaison",
            description="Coordinates review with external agency or department",
            order=3,
        ),
        ApprovalStep(
            role="Public Affairs Officer",
            description="Reviews for communications impact and public messaging",
            order=4,
        ),
        ApprovalStep(
            role="Approving Official",
            description="Final interagency approval and publication authorization",
            order=5,
        ),
    ],
    # Legacy aliases kept for backward compatibility with existing projects
    "branch-coordination": [
        ApprovalStep(
            role="SME",
            description="Subject Matter Expert review and validation",
            order=1,
        ),
        ApprovalStep(
            role="Front Line Manager",
            description="Front Line Manager approval",
            order=2,
        ),
        ApprovalStep(
            role="Product Policy Manager",
            description="Product Policy Manager review and approval",
            order=3,
        ),
        ApprovalStep(
            role="Technical Writer",
            description="Technical Writer review and editing",
            order=4,
        ),
        ApprovalStep(
            role="Senior Technical Writer",
            description="Senior Technical Writer review and approval",
            order=5,
        ),
        ApprovalStep(
            role="Technical Writing Manager",
            description="Technical Writing Manager final approval",
            order=6,
        ),
    ],
    "fast-track-coordination": [
        ApprovalStep(
            role="Writer",
            description="Drafts minor or urgent changes",
            order=1,
        ),
        ApprovalStep(
            role="SME",
            description="Subject Matter Expert review",
            order=2,
        ),
        ApprovalStep(
            role="Senior Technical Writer",
            description="Final review and approval",
            order=3,
        ),
    ],
    "pre-coordination": [
        ApprovalStep(
            role="Writer",
            description="Initial drafting and self-check",
            order=1,
        ),
        ApprovalStep(
            role="Peer Reviewer",
            description="Peer review for technical soundness",
            order=2,
        ),
        ApprovalStep(
            role="Branch Liaison",
            description="Confirms alignment with branch priorities",
            order=3,
        ),
    ],
    "requirements-data-gathering": [
        ApprovalStep(
            role="Research Analyst",
            description="Collects background data and stakeholder requirements",
            order=1,
        ),
        ApprovalStep(
            role="Legal/Regulatory Reviewer",
            description="Identifies statutory constraints",
            order=2,
        ),
        ApprovalStep(
            role="Writer",
            description="Creates annotated outline for downstream reviewers",
            order=3,
        ),
    ],
    "external-partner-coordination": [
        ApprovalStep(
            role="Internal SME",
            description="Internal subject matter expert review",
            order=1,
        ),
        ApprovalStep(
            role="Public Affairs",
            description="Communications and public affairs review",
            order=2,
        ),
        ApprovalStep(
            role="External Stakeholder",
            description="External stakeholder review",
            order=3,
        ),
        ApprovalStep(
            role="Technical Writer",
            description="Incorporates external feedback",
            order=4,
        ),
        ApprovalStep(
            role="Technical Writing Manager",
            description="Final internal approval",
            order=5,
        ),
    ],
    "publication-distribution": [
        ApprovalStep(
            role="Technical Writer",
            description="Prepares publication version",
            order=1,
        ),
        ApprovalStep(
            role="Communications/Outreach",
            description="Distributes to official channels",
            order=2,
        ),
        ApprovalStep(
            role="Records Management",
            description="Archives final version in CMS",
            order=3,
        ),
    ],
    "implementation-tracking": [
        ApprovalStep(
            role="Program Manager",
            description="Notifies affected teams",
            order=1,
        ),
        ApprovalStep(
            role="Compliance Officer",
            description="Confirms procedures updated",
            order=2,
        ),
        ApprovalStep(
            role="Records Management",
            description="Archive and close workflow",
            order=3,
        ),
    ],
}


DEFAULT_WORKFLOW_DESCRIPTIONS: Dict[str, str] = {
    "standard-review": (
        "Full review path for most government documents. Includes author, subject matter expert, "
        "legal/policy counsel, division director, and approving official."
    ),
    "fast-track": (
        "Expedited two-step path for time-sensitive or low-risk documents. "
        "Author drafts; approving official signs with documented justification."
    ),
    "sop-review": (
        "Standard review path for operating procedures. Includes process owner, peer reviewer, "
        "supervisor, and approving official."
    ),
    "inter-agency-coordination": (
        "Review path for documents requiring coordination across agencies or departments. "
        "Includes internal legal review, external agency liaison, and public affairs."
    ),
    # Descriptions for legacy aliases
    "branch-coordination": "Legacy alias — use standard-review for new projects.",
    "fast-track-coordination": "Legacy alias — use fast-track for new projects.",
    "pre-coordination": "Legacy alias — use standard-review for new projects.",
    "requirements-data-gathering": "Legacy alias — use standard-review for new projects.",
    "external-partner-coordination": "Legacy alias — use inter-agency-coordination for new projects.",
    "publication-distribution": "Legacy alias — use standard-review for new projects.",
    "implementation-tracking": "Legacy alias — use standard-review for new projects.",
}


def _log_template_issue(template_name: str, reason: str) -> None:
    """Log workflow template validation issues for operators."""
    try:
        from ..logs import log_event
    except Exception:
        return
    try:
        log_event(
            "workflow_template_invalid",
            severity="error",
            template=template_name,
            reason=reason,
        )
    except Exception:
        pass


def _raise_template_error(template_name: str, reason: str) -> None:
    """Log and raise an error describing template ordering issues."""
    _log_template_issue(template_name, reason)
    raise ValueError(f"Workflow template '{template_name}' has invalid approval order: {reason}")


def _validate_template_orders(template_name: str, steps: List[ApprovalStep]) -> None:
    """Ensure approval steps have strictly increasing integer order values."""
    last_order: int | None = None
    for step in steps:
        order = step.order
        if not isinstance(order, int) or isinstance(order, bool):
            _raise_template_error(
                template_name,
                f"step '{step.role}' uses non-integer order value {order!r}",
            )
        if order < 0:
            _raise_template_error(
                template_name,
                f"step '{step.role}' uses negative order value {order}",
            )
        if last_order is not None and order <= last_order:
            comparison = "duplicate" if order == last_order else "regression"
            _raise_template_error(
                template_name,
                f"step '{step.role}' introduces {comparison}: order {order} after {last_order}",
            )
        last_order = order


def _template_steps_from_definition(template: WorkflowTemplateModel) -> list[ApprovalStep]:
    steps: list[ApprovalStep] = []
    for idx, step in enumerate(template.steps, start=1):
        description = step.description or f"{step.role} review"
        steps.append(
            ApprovalStep(
                role=step.role,
                description=description,
                order=idx,
                required=step.required,
            )
        )
    return steps


def _build_default_template_definitions() -> Dict[str, WorkflowTemplateModel]:
    defaults: Dict[str, WorkflowTemplateModel] = {}
    for name, steps in DEFAULT_WORKFLOW_TEMPLATES.items():
        defaults[name] = WorkflowTemplateModel(
            id=name,
            name=name,
            description=DEFAULT_WORKFLOW_DESCRIPTIONS.get(name),
            steps=[
                WorkflowTemplateStep(
                    role=step.role,
                    required=step.required,
                    description=step.description,
                )
                for step in steps
            ],
        )
    return defaults


def _coerce_template_payload(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and "templates" in payload:
        templates = payload["templates"]
        if isinstance(templates, list):
            return templates
    raise ValueError("Saved workflow templates must be a list or include 'templates'")


def _sync_workflow_templates_from_definitions() -> None:
    workflow_templates.clear()
    for name, template in workflow_template_definitions.items():
        steps = _template_steps_from_definition(template)
        workflow_templates[name] = steps
        _validate_template_orders(name, steps)


def _save_templates_to_db() -> None:
    """Synchronize current workflow template definitions into the DB."""
    try:
        from sqlalchemy import text as _text

        from ..db_store import get_db

        db = get_db()
        with db.session() as conn:
            current_ids = set(workflow_template_definitions)
            for template in workflow_template_definitions.values():
                conn.execute(
                    _text(
                        "INSERT INTO workflow_template_records (id, name, data)"
                        " VALUES (:id, :name, :data)"
                        " ON CONFLICT(id) DO UPDATE SET name=excluded.name, data=excluded.data"
                    ),
                    {
                        "id": template.id,
                        "name": template.name,
                        "data": json.dumps(template.model_dump()),
                    },
                )
            rows = conn.execute(_text("SELECT id FROM workflow_template_records")).fetchall()
            for (template_id,) in rows:
                if template_id not in current_ids:
                    conn.execute(
                        _text("DELETE FROM workflow_template_records WHERE id = :id"),
                        {"id": template_id},
                    )
    except Exception as exc:  # pragma: no cover - best effort
        _logger.warning("Failed to save templates to DB: %s", exc)


def _load_templates_from_db() -> bool:
    """Load workflow templates from the DB into ``workflow_template_definitions``.

    Returns ``True`` if any templates were loaded, ``False`` otherwise.
    """
    try:
        from sqlalchemy import text as _text

        from ..db_store import get_db

        db = get_db()
        with db.session() as conn:
            rows = conn.execute(
                _text("SELECT data FROM workflow_template_records")
            ).fetchall()
        if not rows:
            return False
        for (raw,) in rows:
            data = json.loads(raw) if isinstance(raw, str) else raw
            try:
                template = WorkflowTemplateModel.model_validate(data)
                workflow_template_definitions[template.id] = template
            except Exception as exc:  # pragma: no cover - skip corrupt rows
                _logger.debug("Skipping corrupt template row: %s", exc)
        return bool(workflow_template_definitions)
    except Exception:  # pragma: no cover - DB not available
        return False


def _ensure_templates_loaded() -> None:
    with _TEMPLATES_LOAD_LOCK:
        global _TEMPLATES_LOADED

        if _TEMPLATES_LOADED:
            return

        workflow_template_definitions.clear()
        workflow_template_definitions.update(_build_default_template_definitions())

        if DOCREVIEW360_ENABLE_WORKFLOW_TEMPLATE_PERSISTENCE:
            loaded_from_db = _load_templates_from_db()
            if not loaded_from_db or not workflow_template_definitions:
                workflow_template_definitions.update(_build_default_template_definitions())

        _sync_workflow_templates_from_definitions()
        _TEMPLATES_LOADED = True


def list_workflow_templates() -> list[WorkflowTemplateModel]:
    _ensure_templates_loaded()
    return list(workflow_template_definitions.values())


def get_workflow_template(template_id: str) -> WorkflowTemplateModel | None:
    _ensure_templates_loaded()
    return workflow_template_definitions.get(template_id)


def create_workflow_template(payload: WorkflowTemplatePayload) -> WorkflowTemplateModel:
    _ensure_templates_loaded()
    name = payload.name.strip()
    if name in workflow_template_definitions:
        raise ValueError("Workflow template already exists")
    # Convert steps to dicts to avoid Pydantic class-identity failures after module reloads
    steps_data = [s.model_dump() for s in payload.steps]
    template = WorkflowTemplateModel(
        id=name,
        name=name,
        description=payload.description,
        steps=steps_data,
        updated=datetime.now(timezone.utc).isoformat(),
    )
    workflow_template_definitions[name] = template
    _sync_workflow_templates_from_definitions()
    _save_templates_to_db()
    return template


def update_workflow_template(
    template_id: str, payload: WorkflowTemplatePayload
) -> WorkflowTemplateModel:
    _ensure_templates_loaded()
    if template_id not in workflow_template_definitions:
        raise KeyError("Workflow template not found")
    name = payload.name.strip()
    if name != template_id and name in workflow_template_definitions:
        raise ValueError("Workflow template name already exists")
    steps_data = [s.model_dump() for s in payload.steps]
    template = WorkflowTemplateModel(
        id=name,
        name=name,
        description=payload.description,
        steps=steps_data,
        updated=datetime.now(timezone.utc).isoformat(),
    )
    if name != template_id:
        workflow_template_definitions.pop(template_id, None)
    workflow_template_definitions[name] = template
    _sync_workflow_templates_from_definitions()
    _save_templates_to_db()
    return template


def delete_workflow_template(template_id: str) -> None:
    _ensure_templates_loaded()
    if template_id not in workflow_template_definitions:
        raise KeyError("Workflow template not found")
    workflow_template_definitions.pop(template_id)
    workflow_templates.pop(template_id, None)
    _sync_workflow_templates_from_definitions()
    _save_templates_to_db()


def reset_workflow_templates(*, keep_file: bool = False) -> None:  # noqa: ARG001
    """Reset workflow templates to defaults.

    ``keep_file`` is accepted for backwards compatibility but has no effect:
    templates are persisted to the database only.
    """
    global _TEMPLATES_LOADED
    _TEMPLATES_LOADED = False
    workflow_template_definitions.clear()
    workflow_templates.clear()
    _ensure_templates_loaded()
