# SPDX-License-Identifier: MIT
"""Organization-defined custom workflow templates without code changes."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from .models import CustomWorkflowTemplate


def validate_workflow_steps(steps: list[dict[str, Any]]) -> list[str]:
    """Validate workflow step definitions. Returns a list of error messages (empty = valid)."""
    errors: list[str] = []
    if not steps:
        errors.append("Workflow must have at least one step")
        return errors
    seen_names: set[str] = set()
    for i, step in enumerate(steps):
        prefix = f"Step {i + 1}"
        if not isinstance(step, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        step_name = step.get("step_name")
        if not step_name or not isinstance(step_name, str):
            errors.append(f"{prefix}: 'step_name' is required and must be a non-empty string")
        elif step_name in seen_names:
            errors.append(f"{prefix}: duplicate step_name '{step_name}'")
        else:
            seen_names.add(step_name)

        role = step.get("role_required")
        if not role or not isinstance(role, str):
            errors.append(f"{prefix}: 'role_required' is required and must be a non-empty string")

        sla_days = step.get("sla_days")
        if sla_days is not None:
            if not isinstance(sla_days, (int, float)) or sla_days <= 0:
                errors.append(f"{prefix}: 'sla_days' must be a positive number if provided")

    return errors


def create_custom_workflow(
    db: Session,
    org_id: str,
    name: str,
    steps: list[dict[str, Any]],
    description: str | None = None,
    doc_types: list[str] | None = None,
    created_by: str = "system",
) -> CustomWorkflowTemplate:
    """Create a custom workflow template for an organization."""
    errors = validate_workflow_steps(steps)
    if errors:
        raise ValueError(f"Invalid workflow steps: {'; '.join(errors)}")

    now = datetime.now(timezone.utc)
    record = CustomWorkflowTemplate(
        id=str(uuid.uuid4()),
        org_id=org_id,
        name=name,
        description=description,
        steps=json.dumps(steps),
        doc_types=json.dumps(doc_types) if doc_types is not None else None,
        created_by=created_by,
        created_at=now,
        is_active=True,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_custom_workflow(
    db: Session, org_id: str, name: str
) -> CustomWorkflowTemplate | None:
    """Retrieve a custom workflow template by org + name."""
    return (
        db.query(CustomWorkflowTemplate)
        .filter(
            CustomWorkflowTemplate.org_id == org_id,
            CustomWorkflowTemplate.name == name,
        )
        .first()
    )


def list_custom_workflows(
    db: Session, org_id: str, doc_type: str | None = None
) -> list[CustomWorkflowTemplate]:
    """List active custom workflow templates for an organization."""
    q = db.query(CustomWorkflowTemplate).filter(
        CustomWorkflowTemplate.org_id == org_id,
        CustomWorkflowTemplate.is_active.is_(True),
    )
    results = q.order_by(CustomWorkflowTemplate.name).all()
    if doc_type is None:
        return results
    # Filter by doc_type applicability
    filtered = []
    for r in results:
        if r.doc_types is None:
            filtered.append(r)
        else:
            applicable = json.loads(r.doc_types)
            if doc_type in applicable:
                filtered.append(r)
    return filtered


def update_custom_workflow(
    db: Session, org_id: str, name: str, **kwargs: Any
) -> CustomWorkflowTemplate:
    """Update fields on a custom workflow template."""
    record = get_custom_workflow(db, org_id, name)
    if record is None:
        raise ValueError(f"Custom workflow '{name}' not found for org '{org_id}'")

    now = datetime.now(timezone.utc)
    allowed = {"description", "is_active"}
    for key, value in kwargs.items():
        if key == "steps":
            errors = validate_workflow_steps(value)
            if errors:
                raise ValueError(f"Invalid workflow steps: {'; '.join(errors)}")
            record.steps = json.dumps(value)
        elif key == "doc_types":
            record.doc_types = json.dumps(value) if value is not None else None
        elif key in allowed:
            setattr(record, key, value)
    record.updated_at = now
    db.commit()
    db.refresh(record)
    return record


def delete_custom_workflow(db: Session, org_id: str, name: str) -> bool:
    """Delete a custom workflow template. Returns True if deleted."""
    record = get_custom_workflow(db, org_id, name)
    if record is None:
        return False
    db.delete(record)
    db.commit()
    return True
