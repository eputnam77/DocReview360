# SPDX-License-Identifier: MIT
"""Organization-defined custom fields for documents, projects, and users (EAV pattern)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from .models import CustomFieldDefinition, CustomFieldValue

VALID_ENTITY_TYPES = frozenset(["document", "project", "user"])
VALID_FIELD_TYPES = frozenset(["text", "number", "date", "boolean", "select"])


def create_field_definition(
    db: Session,
    org_id: str,
    entity_type: str,
    field_name: str,
    field_label: str,
    field_type: str,
    options: list[str] | None = None,
    required: bool = False,
    default_value: Any = None,
    sort_order: int = 0,
    created_by: str = "system",
) -> CustomFieldDefinition:
    """Create a new custom field definition for an organization."""
    if entity_type not in VALID_ENTITY_TYPES:
        raise ValueError(f"entity_type must be one of {sorted(VALID_ENTITY_TYPES)}")
    if field_type not in VALID_FIELD_TYPES:
        raise ValueError(f"field_type must be one of {sorted(VALID_FIELD_TYPES)}")
    if field_type == "select" and not options:
        raise ValueError("'options' is required for field_type='select'")

    now = datetime.now(timezone.utc)
    defn = CustomFieldDefinition(
        id=str(uuid.uuid4()),
        org_id=org_id,
        entity_type=entity_type,
        field_name=field_name,
        field_label=field_label,
        field_type=field_type,
        options=json.dumps(options) if options is not None else None,
        required=required,
        default_value=json.dumps(default_value) if default_value is not None else None,
        sort_order=sort_order,
        is_active=True,
        created_by=created_by,
        created_at=now,
    )
    db.add(defn)
    db.commit()
    db.refresh(defn)
    return defn


def list_field_definitions(
    db: Session, org_id: str, entity_type: str | None = None
) -> list[CustomFieldDefinition]:
    """List active custom field definitions for an org, optionally filtered by entity_type."""
    q = db.query(CustomFieldDefinition).filter(
        CustomFieldDefinition.org_id == org_id,
        CustomFieldDefinition.is_active.is_(True),
    )
    if entity_type is not None:
        q = q.filter(CustomFieldDefinition.entity_type == entity_type)
    return q.order_by(CustomFieldDefinition.sort_order, CustomFieldDefinition.field_name).all()


def get_field_definition(
    db: Session, org_id: str, entity_type: str, field_name: str
) -> CustomFieldDefinition | None:
    """Retrieve a specific custom field definition."""
    return (
        db.query(CustomFieldDefinition)
        .filter(
            CustomFieldDefinition.org_id == org_id,
            CustomFieldDefinition.entity_type == entity_type,
            CustomFieldDefinition.field_name == field_name,
        )
        .first()
    )


def delete_field_definition(db: Session, org_id: str, field_id: str) -> bool:
    """Soft-delete a field definition (marks is_active=False). Returns True if found."""
    defn = (
        db.query(CustomFieldDefinition)
        .filter(CustomFieldDefinition.id == field_id, CustomFieldDefinition.org_id == org_id)
        .first()
    )
    if defn is None:
        return False
    defn.is_active = False
    db.commit()
    return True


def validate_field_value(field_def: CustomFieldDefinition, value: Any) -> str | None:
    """Validate a value against its field definition. Returns error message or None."""
    if value is None:
        if field_def.required:
            return f"Field '{field_def.field_name}' is required"
        return None

    if field_def.field_type == "number":
        try:
            float(value)
        except (TypeError, ValueError):
            return f"Field '{field_def.field_name}' must be a number"

    elif field_def.field_type == "boolean":
        if not isinstance(value, bool):
            return f"Field '{field_def.field_name}' must be a boolean"

    elif field_def.field_type == "select":
        if field_def.options:
            allowed = json.loads(field_def.options)
            if value not in allowed:
                return f"Field '{field_def.field_name}' must be one of: {', '.join(allowed)}"

    elif field_def.field_type == "date":
        if isinstance(value, str):
            try:
                datetime.fromisoformat(value)
            except ValueError:
                return f"Field '{field_def.field_name}' must be an ISO date string"

    return None


def set_field_value(
    db: Session, field_id: str, entity_id: str, value: Any, updated_by: str
) -> CustomFieldValue:
    """Set the value of a custom field for a specific entity (upsert)."""
    now = datetime.now(timezone.utc)
    row = (
        db.query(CustomFieldValue)
        .filter(
            CustomFieldValue.field_id == field_id,
            CustomFieldValue.entity_id == entity_id,
        )
        .first()
    )
    if row is None:
        row = CustomFieldValue(
            id=str(uuid.uuid4()),
            field_id=field_id,
            entity_id=entity_id,
        )
        db.add(row)
    row.value = json.dumps(value) if value is not None else None
    row.updated_by = updated_by
    row.updated_at = now
    db.commit()
    db.refresh(row)
    return row


def get_field_values(
    db: Session, entity_id: str, org_id: str, entity_type: str
) -> dict[str, Any]:
    """Return a dict of {field_name: value} for an entity's custom fields."""
    defns = list_field_definitions(db, org_id, entity_type=entity_type)
    if not defns:
        return {}
    defn_map = {d.id: d for d in defns}
    values = (
        db.query(CustomFieldValue)
        .filter(
            CustomFieldValue.entity_id == entity_id,
            CustomFieldValue.field_id.in_(defn_map.keys()),
        )
        .all()
    )
    result: dict[str, Any] = {}
    for row in values:
        defn = defn_map.get(row.field_id)
        if defn:
            result[defn.field_name] = json.loads(row.value) if row.value is not None else None
    # Include defaults for fields not yet set
    for defn in defns:
        if defn.field_name not in result:
            result[defn.field_name] = (
                json.loads(defn.default_value) if defn.default_value is not None else None
            )
    return result
