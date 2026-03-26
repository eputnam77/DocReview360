# SPDX-License-Identifier: MIT
"""Manage golden Markdown templates (Task 143)."""

from __future__ import annotations

import difflib
import json
import os
import threading
from base64 import b64decode, b64encode
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy import text as _text

TEMPLATES_DIR = Path(os.getenv("DOCREVIEW360_TEMPLATES_DIR", "templates/golden"))


def _env_flag_enabled(value: str | None) -> bool:
    """Interpret truthy string values for the persistence feature flag."""

    if value is None:
        return True
    normalized = value.strip().lower()
    return normalized not in {"0", "false", "no", "off"}


DOCREVIEW360_ENABLE_TEMPLATE_PERSISTENCE = _env_flag_enabled(
    os.getenv("DOCREVIEW360_ENABLE_TEMPLATE_PERSISTENCE")
)

_TEMPLATES_LOADED: bool = False
# Guards the _TEMPLATES_LOADED flag to prevent duplicate loads under concurrent requests.
_TEMPLATE_LOAD_LOCK = threading.Lock()
# Optional file-based cache path; can be overridden in tests for isolation.
_ACTIVE_TEMPLATES_FILE: Path | None = None


def save_template(name: str, content: str, root: Path = TEMPLATES_DIR) -> Path:
    """Save ``content`` under ``name`` in ``root`` and return the path."""

    if not isinstance(name, str) or not name.strip():
        raise ValueError("name is required")

    stem = Path(name.strip())
    if stem.is_absolute() or len(stem.parts) != 1 or stem.parts[0] in {"..", "."}:
        raise ValueError("name must be a simple file name")

    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{stem.name}.md"
    path.write_text(content)
    return path


def list_templates(root: Path = TEMPLATES_DIR) -> List[str]:
    """Return available template names."""
    if not root.exists():
        return []
    return [p.stem for p in root.glob("*.md")]


@dataclass
class TemplateVersion:
    """Stored template content with version and metadata."""

    version: int
    content: bytes
    metadata: Dict[str, Any]
    approved: bool = False
    retired: bool = False
    change_summary: str = ""


_template_store: dict[str, List[TemplateVersion]] = {}

# ---------------------------------------------------------------------------
# Template phase locks
# ---------------------------------------------------------------------------

# Maps (template_name, phase) -> True meaning the template is locked for that phase
_template_phase_locks: dict[tuple[str, str], bool] = {}


def lock_template_for_phase(name: str, phase: str) -> None:
    """Prevent modifications to *name* while the project is in *phase*."""
    if not name or not phase:
        raise ValueError("name and phase are required")
    _template_phase_locks[(name, phase)] = True


def unlock_template_for_phase(name: str, phase: str) -> None:
    """Remove the phase lock for *name* in *phase*."""
    if not name or not phase:
        raise ValueError("name and phase are required")
    _template_phase_locks.pop((name, phase), None)


def is_template_locked_for_phase(name: str, phase: str) -> bool:
    """Return ``True`` if *name* is locked for *phase*."""
    return bool(_template_phase_locks.get((name, phase)))


def get_template_phase_locks(name: str) -> list[str]:
    """Return all phases that currently lock *name*."""
    return [phase for (tname, phase) in _template_phase_locks if tname == name]


def reset_template_phase_locks() -> None:
    """Clear all phase locks (used in tests)."""
    _template_phase_locks.clear()


def _serialize_template_store() -> dict[str, list[dict[str, Any]]]:
    return {
        name: [
            {
                "version": version.version,
                "content": b64encode(version.content).decode("ascii"),
                "metadata": version.metadata,
                "approved": version.approved,
                "retired": version.retired,
                "change_summary": version.change_summary,
            }
            for version in versions
        ]
        for name, versions in _template_store.items()
    }


def _deserialize_versions(versions_data: list[dict[str, Any]]) -> List[TemplateVersion]:
    parsed = []
    for entry in versions_data:
        parsed.append(
            TemplateVersion(
                version=entry["version"],
                content=b64decode(entry["content"]),
                metadata=entry.get("metadata", {}),
                approved=entry.get("approved", False),
                retired=entry.get("retired", False),
                change_summary=entry.get("change_summary", ""),
            )
        )
    return parsed


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _get_db():  # type: ignore[return]
    from .db_store import get_db
    return get_db()


def _load_from_db() -> bool:
    """Load template versions from the database. Returns True if any loaded."""
    try:
        db = _get_db()
        with db.session() as conn:
            rows = conn.execute(
                _text("SELECT name, versions FROM golden_template_records")
            ).fetchall()
        if not rows:
            return False
        for row in rows:
            name = row[0]
            raw = row[1]
            versions_data = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(versions_data, list):
                _template_store[name] = _deserialize_versions(versions_data)
        return bool(_template_store)
    except Exception:  # pragma: no cover - DB not available
        return False


def _save_to_db() -> None:
    """Upsert the entire in-memory template store into the database."""
    if not DOCREVIEW360_ENABLE_TEMPLATE_PERSISTENCE:
        return
    try:
        db = _get_db()
        with db.session() as conn:
            for name, versions in _template_store.items():
                serialized = json.dumps(_serialize_template_store().get(name, []))
                conn.execute(
                    _text(
                        "INSERT INTO golden_template_records (name, versions)"
                        " VALUES (:name, :versions)"
                        " ON CONFLICT(name) DO UPDATE SET versions=excluded.versions"
                    ),
                    {"name": name, "versions": serialized},
                )
    except Exception:  # pragma: no cover - best effort
        pass


def _delete_from_db(name: str) -> None:
    if not DOCREVIEW360_ENABLE_TEMPLATE_PERSISTENCE:
        return
    try:
        db = _get_db()
        with db.session() as conn:
            conn.execute(
                _text("DELETE FROM golden_template_records WHERE name = :name"),
                {"name": name},
            )
    except Exception:  # pragma: no cover - best effort
        pass


def _load_template_store() -> None:
    with _TEMPLATE_LOAD_LOCK:
        global _TEMPLATES_LOADED
        if _TEMPLATES_LOADED or not DOCREVIEW360_ENABLE_TEMPLATE_PERSISTENCE:
            return
        _load_from_db()
        _TEMPLATES_LOADED = True


def _save_template_store() -> None:
    _save_to_db()


def reset_template_store(keep_file: bool = False, root: Any = None) -> None:  # noqa: ARG001
    """Reset the in-memory store.

    ``keep_file`` and ``root`` are accepted for backwards compatibility but
    have no effect: templates are persisted to the database only.
    """
    global _TEMPLATES_LOADED
    _template_store.clear()
    _TEMPLATES_LOADED = False


def _compute_change_summary(old_content: bytes, new_content: bytes) -> str:
    """Return a human-readable unified-diff summary between two content blobs."""
    old_lines = old_content.decode("utf-8", errors="replace").splitlines(keepends=True)
    new_lines = new_content.decode("utf-8", errors="replace").splitlines(keepends=True)
    diff = list(
        difflib.unified_diff(old_lines, new_lines, fromfile="previous", tofile="current", n=1)
    )
    if not diff:
        return "no changes detected"
    summary_lines = diff[:10]
    summary = "".join(summary_lines)
    if len(diff) > 10:
        summary += f"\n... ({len(diff) - 10} more diff lines)"
    return summary.strip()


def upload_template(
    name: str, data: bytes, metadata: Dict[str, Any] | None = None
) -> TemplateVersion:
    """Store ``data`` and ``metadata`` as a new version for ``name``."""
    _load_template_store()
    if not name:
        raise ValueError("name is required")
    if metadata is not None and not isinstance(metadata, dict):
        raise ValueError("metadata must be a mapping")

    # Enforce phase locks
    phase = (metadata or {}).get("phase", "")
    if phase and is_template_locked_for_phase(name, phase):
        raise PermissionError(
            f"template '{name}' is locked for phase '{phase}' and cannot be modified"
        )

    versions = _template_store.setdefault(name, [])
    version = len(versions) + 1

    change_summary = ""
    if versions:
        change_summary = _compute_change_summary(versions[-1].content, data)

    record = TemplateVersion(
        version=version,
        content=data,
        metadata=(deepcopy(metadata) if metadata else {}),
        change_summary=change_summary,
    )
    versions.append(record)
    _save_template_store()
    return record


def approve_template(name: str) -> TemplateVersion:
    """Mark the latest version of ``name`` as approved."""

    _load_template_store()
    ver = get_latest_template(name)
    if not ver:
        raise ValueError("template not found")
    ver.approved = True
    _save_template_store()
    return ver


def retire_template(name: str) -> TemplateVersion:
    """Mark the latest version of ``name`` as retired."""

    _load_template_store()
    ver = get_latest_template(name)
    if not ver:
        raise ValueError("template not found")
    ver.retired = True
    _save_template_store()
    return ver


def get_latest_template(name: str) -> TemplateVersion | None:
    """Return the most recent template for ``name`` if it exists."""

    _load_template_store()
    versions = _template_store.get(name)
    if not versions:
        return None
    return versions[-1]


def list_template_versions(name: str) -> List[TemplateVersion]:
    """Return all stored versions for ``name``."""

    _load_template_store()
    return list(_template_store.get(name, []))


def list_stored_templates() -> Dict[str, TemplateVersion]:
    """Return the latest version for each stored template."""

    _load_template_store()
    return {name: versions[-1] for name, versions in _template_store.items()}


def delete_template(name: str) -> None:
    """Delete all stored versions for ``name``."""

    _load_template_store()
    if name not in _template_store:
        raise KeyError(f"template '{name}' not found")
    _template_store.pop(name, None)
    _delete_from_db(name)
