# SPDX-License-Identifier: MIT
"""Manage email templates used for notifications."""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Any, Dict, List

from sqlalchemy import text as _text


@dataclass
class EmailTemplate:
    name: str
    subject: str
    body: str
    task: str | None = None


def _env_flag_enabled(value: str | None) -> bool:
    """Interpret truthy string values for the persistence feature flag."""

    if value is None:
        return True
    normalized = value.strip().lower()
    return normalized not in {"0", "false", "no", "off"}


DOCREVIEW360_ENABLE_EMAIL_TEMPLATE_PERSISTENCE = _env_flag_enabled(
    os.getenv("DOCREVIEW360_ENABLE_EMAIL_TEMPLATE_PERSISTENCE")
)

_EMAIL_TEMPLATES_LOADED: bool = False
# Guards the _EMAIL_TEMPLATES_LOADED flag to prevent duplicate loads under concurrent requests.
_EMAIL_TEMPLATE_LOAD_LOCK = threading.Lock()

TEMPLATES: Dict[str, EmailTemplate] = {}


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _get_db():  # type: ignore[return]
    from .db_store import get_db
    return get_db()


def _load_from_db() -> bool:
    """Load templates from the database. Returns True if any were loaded."""
    try:
        db = _get_db()
        with db.session() as conn:
            rows = conn.execute(
                _text("SELECT name, subject, body, task FROM email_template_records")
            ).fetchall()
        if not rows:
            return False
        for row in rows:
            tmpl = EmailTemplate(name=row[0], subject=row[1], body=row[2], task=row[3])
            TEMPLATES[tmpl.name] = tmpl
        return True
    except Exception:  # pragma: no cover - DB not available
        return False


def _save_to_db() -> None:
    """Upsert all in-memory templates into the database."""
    if not DOCREVIEW360_ENABLE_EMAIL_TEMPLATE_PERSISTENCE:
        return
    try:
        db = _get_db()
        with db.session() as conn:
            for tmpl in TEMPLATES.values():
                conn.execute(
                    _text(
                        "INSERT INTO email_template_records (name, subject, body, task)"
                        " VALUES (:name, :subject, :body, :task)"
                        " ON CONFLICT(name) DO UPDATE SET"
                        "  subject=excluded.subject,"
                        "  body=excluded.body,"
                        "  task=excluded.task"
                    ),
                    {"name": tmpl.name, "subject": tmpl.subject, "body": tmpl.body, "task": tmpl.task},
                )
    except Exception:  # pragma: no cover - best effort
        pass


def _delete_from_db(name: str) -> None:
    if not DOCREVIEW360_ENABLE_EMAIL_TEMPLATE_PERSISTENCE:
        return
    try:
        db = _get_db()
        with db.session() as conn:
            conn.execute(
                _text("DELETE FROM email_template_records WHERE name = :name"),
                {"name": name},
            )
    except Exception:  # pragma: no cover - best effort
        pass


def _load_templates() -> None:
    with _EMAIL_TEMPLATE_LOAD_LOCK:
        global _EMAIL_TEMPLATES_LOADED
        if _EMAIL_TEMPLATES_LOADED or not DOCREVIEW360_ENABLE_EMAIL_TEMPLATE_PERSISTENCE:
            return
        _load_from_db()
        _EMAIL_TEMPLATES_LOADED = True


def reset_email_templates(keep_file: bool = False, root: Any = None) -> None:  # noqa: ARG001
    """Reset the in-memory templates.

    ``keep_file`` and ``root`` are accepted for backwards compatibility but
    have no effect: templates are persisted to the database only.
    """
    global _EMAIL_TEMPLATES_LOADED
    TEMPLATES.clear()
    _EMAIL_TEMPLATES_LOADED = False


def create_template(name: str, subject: str, body: str, task: str | None = None) -> EmailTemplate:
    """Create and register a new template."""
    _load_templates()
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
    _save_to_db()
    return template


def get_template(name: str) -> EmailTemplate | None:
    """Return a template by ``name`` if it exists."""
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
    """Update fields of an existing template and return it."""

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
    _save_to_db()
    return tmpl


def delete_template(name: str) -> None:
    """Remove ``name`` from the registry."""
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
    _delete_from_db(name)


def list_templates() -> List[EmailTemplate]:
    """Return all templates in creation order."""
    _load_templates()
    return list(TEMPLATES.values())
