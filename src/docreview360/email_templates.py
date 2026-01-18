"""Manage email templates used for notifications."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class EmailTemplate:
    name: str
    subject: str
    body: str
    task: str | None = None


TEMPLATES: Dict[str, EmailTemplate] = {}


def create_template(name: str, subject: str, body: str, task: str | None = None) -> EmailTemplate:
    """Create and register a new template."""
    # ``dataclasses`` do not enforce type annotations at runtime which meant
    # callers could accidentally pass non-string values for ``subject`` or
    # ``body`` and end up with malformed templates.  Additionally a name
    # consisting solely of whitespace previously slipped through the simple
    # truthiness check.  Validate the inputs explicitly to avoid subtle bugs in
    # downstream formatting code.
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name required")
    if not isinstance(subject, str):
        raise TypeError("subject must be a string")
    if not subject.strip():
        raise ValueError("subject required")
    if not isinstance(body, str):
        raise TypeError("body must be a string")
    if not body.strip():
        raise ValueError("body required")
    if task is not None and not isinstance(task, str):
        raise TypeError("task must be a string or None")
    name = name.strip()
    if name in TEMPLATES:
        raise ValueError(f"template '{name}' already exists")
    template = EmailTemplate(name=name, subject=subject, body=body, task=task)
    TEMPLATES[name] = template
    return template


def get_template(name: str) -> EmailTemplate | None:
    """Return a template by ``name`` if it exists.

    ``create_template`` normalises template names by stripping surrounding
    whitespace.  Callers passing a name with incidental spaces to
    :func:`get_template` would therefore fail to retrieve an existing
    template even though :func:`create_template` accepted it.  Normalise the
    lookup key here so the API behaves consistently regardless of
    whitespace around the provided name.
    """
    if not isinstance(name, str):
        raise TypeError("name must be a string")
    return TEMPLATES.get(name.strip())


_UNSET: Any = object()


def update_template(  # noqa: C901
    name: str,
    subject: str | None | Any = _UNSET,
    body: str | None | Any = _UNSET,
    task: str | None | Any = _UNSET,
) -> EmailTemplate:
    """Update fields of an existing template and return it.

    Using a sentinel allows callers to explicitly clear optional fields by
    passing ``None``. Previously ``task=None`` was indistinguishable from the
    default argument, making it impossible to remove an assigned task from a
    template.
    """

    if not isinstance(name, str):
        raise TypeError("name must be a string")
    name = name.strip()
    tmpl = TEMPLATES.get(name)
    if tmpl is None:
        raise KeyError(f"template '{name}' not found")
    if subject is not _UNSET:
        if not isinstance(subject, str):
            raise TypeError("subject must be a string")
        if not subject.strip():
            raise ValueError("subject required")
        tmpl.subject = subject
    if body is not _UNSET:
        if not isinstance(body, str):
            raise TypeError("body must be a string")
        if not body.strip():
            raise ValueError("body required")
        tmpl.body = body
    if task is not _UNSET:
        if task is not None and not isinstance(task, str):
            raise TypeError("task must be a string or None")
        tmpl.task = task
    return tmpl


def delete_template(name: str) -> None:
    """Remove ``name`` from the registry.

    Similar to :func:`get_template`, callers may accidentally include
    surrounding whitespace when deleting templates.  The previous
    implementation attempted the deletion with the unmodified string which
    resulted in a ``KeyError`` even though the template existed.  Strip the
    name first so lookups are consistent across the module.
    """
    if not isinstance(name, str):
        raise TypeError("name must be a string")
    name = name.strip()
    if not name:
        raise ValueError("name is required")
    try:
        del TEMPLATES[name]
    except KeyError as exc:
        raise KeyError(f"template '{name}' not found") from exc


def list_templates() -> List[EmailTemplate]:
    """Return all templates in creation order."""
    return list(TEMPLATES.values())
