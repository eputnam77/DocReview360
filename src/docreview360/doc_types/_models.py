# SPDX-License-Identifier: MIT
"""Document type Pydantic models."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field, ValidationError, computed_field, field_validator


class DocumentTypeModel(BaseModel):
    """Schema for document types with optional default template linkage."""

    name: str
    template: str
    workflow: List[str] = Field(default_factory=list)
    default_workflow_template_id: str | None = None

    @computed_field(return_type=str)
    def id(self) -> str:  # noqa: A003
        """Expose ``name`` under an ``id`` field for frontend compatibility."""
        return self.name

    @computed_field(return_type=list[str])
    def phases(self) -> list[str]:
        """Surface ``workflow`` as ``phases`` for consumers expecting that key."""
        return self.workflow


class _WorkflowPayload(BaseModel):
    """Validation shim to enforce valid workflow phase values."""

    workflow: List[str]

    @field_validator("workflow")
    @classmethod
    def ensure_non_empty(cls, value: List[str]) -> List[str]:
        if not value:
            raise ValueError("Workflow must include at least one phase")
        for phase in value:
            if not isinstance(phase, str) or not phase.strip():
                raise ValueError("Workflow phases must be non-empty strings")
        return value


def _validate_workflow(doc_type: DocumentTypeModel) -> None:
    """Raise :class:`ValidationError` if *doc_type* has invalid workflow phases."""
    try:
        _WorkflowPayload.model_validate({"workflow": doc_type.workflow})
    except ValidationError as exc:  # pragma: no cover - defensive
        raise ValidationError.from_exception_data(
            DocumentTypeModel.__name__, exc.errors()
        ) from exc
