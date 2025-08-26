"""Manage email templates used for notifications."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class EmailTemplate:
    name: str
    subject: str
    body: str
    task: str | None = None


TEMPLATES: Dict[str, EmailTemplate] = {}


def create_template(name: str, subject: str, body: str, task: str | None = None) -> EmailTemplate:
    """Create and register a new template."""
    if not name:
        raise ValueError("name required")
    if name in TEMPLATES:
        raise ValueError(f"template '{name}' already exists")
    template = EmailTemplate(name=name, subject=subject, body=body, task=task)
    TEMPLATES[name] = template
    return template


def get_template(name: str) -> EmailTemplate | None:
    """Return a template by ``name`` if it exists."""
    return TEMPLATES.get(name)


def update_template(
    name: str, subject: str | None = None, body: str | None = None, task: str | None = None
) -> EmailTemplate:
    """Update fields of an existing template and return it."""
    tmpl = TEMPLATES.get(name)
    if tmpl is None:
        raise KeyError(f"template '{name}' not found")
    if subject is not None:
        tmpl.subject = subject
    if body is not None:
        tmpl.body = body
    if task is not None:
        tmpl.task = task
    return tmpl


def delete_template(name: str) -> None:
    """Remove ``name`` from the registry."""
    try:
        del TEMPLATES[name]
    except KeyError as exc:
        raise KeyError(f"template '{name}' not found") from exc


def list_templates() -> List[EmailTemplate]:
    """Return all templates in creation order."""
    return list(TEMPLATES.values())
