"""Manage email templates used for notifications."""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from filelock import FileLock


@dataclass
class EmailTemplate:
    name: str
    subject: str
    body: str
    task: str | None = None


EMAIL_TEMPLATES_FILE = Path("email_templates.json")


def _env_flag_enabled(value: str | None) -> bool:
    """Interpret truthy string values for the persistence feature flag."""

    if value is None:
        return True
    normalized = value.strip().lower()
    return normalized not in {"0", "false", "no", "off"}


DOCREVIEW360_ENABLE_EMAIL_TEMPLATE_PERSISTENCE = _env_flag_enabled(
    os.getenv("DOCREVIEW360_ENABLE_EMAIL_TEMPLATE_PERSISTENCE")
)

_ACTIVE_EMAIL_TEMPLATES_FILE: Path = EMAIL_TEMPLATES_FILE
_EMAIL_TEMPLATES_LOADED: bool = False
# Guards the _EMAIL_TEMPLATES_LOADED flag to prevent duplicate loads under concurrent requests.
_EMAIL_TEMPLATE_LOAD_LOCK = threading.Lock()

TEMPLATES: Dict[str, EmailTemplate] = {}


def _serialize_templates() -> list[dict[str, Any]]:
    return [
        {
            "name": template.name,
            "subject": template.subject,
            "body": template.body,
            "task": template.task,
        }
        for template in TEMPLATES.values()
    ]


def _load_templates() -> None:
    with _EMAIL_TEMPLATE_LOAD_LOCK:
        global _EMAIL_TEMPLATES_LOADED
        if _EMAIL_TEMPLATES_LOADED or not DOCREVIEW360_ENABLE_EMAIL_TEMPLATE_PERSISTENCE:
            return
        if not _ACTIVE_EMAIL_TEMPLATES_FILE.exists():
            _EMAIL_TEMPLATES_LOADED = True
            return
        lock = FileLock(f"{_ACTIVE_EMAIL_TEMPLATES_FILE}.lock")
        with lock:
            data = json.loads(_ACTIVE_EMAIL_TEMPLATES_FILE.read_text())
        TEMPLATES.clear()
        for entry in data:
            template = EmailTemplate(
                name=entry["name"],
                subject=entry["subject"],
                body=entry["body"],
                task=entry.get("task"),
            )
            TEMPLATES[template.name] = template
        _EMAIL_TEMPLATES_LOADED = True


def _save_templates() -> None:
    if not DOCREVIEW360_ENABLE_EMAIL_TEMPLATE_PERSISTENCE:
        return
    _ACTIVE_EMAIL_TEMPLATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(f"{_ACTIVE_EMAIL_TEMPLATES_FILE}.lock")
    with lock:
        _ACTIVE_EMAIL_TEMPLATES_FILE.write_text(json.dumps(_serialize_templates(), indent=2))


def reset_email_templates(keep_file: bool = False, root: Path | None = None) -> None:
    """Reset the in-memory templates and optionally remove persisted file."""
    global _EMAIL_TEMPLATES_LOADED, _ACTIVE_EMAIL_TEMPLATES_FILE

    if root is not None:
        _ACTIVE_EMAIL_TEMPLATES_FILE = root
    TEMPLATES.clear()
    _EMAIL_TEMPLATES_LOADED = False
    if not keep_file and _ACTIVE_EMAIL_TEMPLATES_FILE.exists():
        _ACTIVE_EMAIL_TEMPLATES_FILE.unlink()
    lock_path = Path(f"{_ACTIVE_EMAIL_TEMPLATES_FILE}.lock")
    if lock_path.exists():
        lock_path.unlink()


def create_template(name: str, subject: str, body: str, task: str | None = None) -> EmailTemplate:
    """Create and register a new template."""
    _load_templates()
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
    _save_templates()
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
    _load_templates()
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

    _load_templates()
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
    _save_templates()
    return tmpl


def delete_template(name: str) -> None:
    """Remove ``name`` from the registry.

    Similar to :func:`get_template`, callers may accidentally include
    surrounding whitespace when deleting templates.  The previous
    implementation attempted the deletion with the unmodified string which
    resulted in a ``KeyError`` even though the template existed.  Strip the
    name first so lookups are consistent across the module.
    """
    _load_templates()
    if not isinstance(name, str):
        raise TypeError("name must be a string")
    name = name.strip()
    if not name:
        raise ValueError("name is required")
    try:
        del TEMPLATES[name]
    except KeyError as exc:
        raise KeyError(f"template '{name}' not found") from exc
    _save_templates()


def list_templates() -> List[EmailTemplate]:
    """Return all templates in creation order."""
    _load_templates()
    return list(TEMPLATES.values())
