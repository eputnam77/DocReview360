"""Manage golden Markdown templates (Task 143)."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from .stubs import record_task_completion

TEMPLATES_DIR = Path("templates/golden")


def save_template(name: str, content: str, root: Path = TEMPLATES_DIR) -> Path:
    """Save ``content`` under ``name`` in ``root`` and return the path.

    ``name`` previously accepted arbitrary strings which allowed directory
    traversal like ``"../evil"`` or subdirectory components such as
    ``"foo/bar"``.  This could write files outside the intended template
    directory.  Restrict names to simple file stems by validating with
    :class:`pathlib.Path` and rejecting any values that resolve to multiple
    parts or special references.  Names consisting solely of whitespace were
    also inadvertently accepted, creating files that were awkward to manage.
    """

    if not isinstance(name, str) or not name.strip():
        raise ValueError("name is required")

    stem = Path(name.strip())
    if stem.is_absolute() or len(stem.parts) != 1 or stem.parts[0] in {"..", "."}:
        raise ValueError("name must be a simple file name")

    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{stem.name}.md"
    path.write_text(content)
    record_task_completion(143)
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


_template_store: dict[str, List[TemplateVersion]] = {}


def upload_template(
    name: str, data: bytes, metadata: Dict[str, Any] | None = None
) -> TemplateVersion:
    """Store ``data`` and ``metadata`` as a new version for ``name``."""

    if not name:
        raise ValueError("name is required")
    if metadata is not None and not isinstance(metadata, dict):
        raise ValueError("metadata must be a mapping")
    versions = _template_store.setdefault(name, [])
    version = len(versions) + 1
    record = TemplateVersion(
        version=version,
        content=data,
        metadata=(deepcopy(metadata) if metadata else {}),
    )
    versions.append(record)
    return record


def approve_template(name: str) -> TemplateVersion:
    """Mark the latest version of ``name`` as approved."""

    ver = get_latest_template(name)
    if not ver:
        raise ValueError("template not found")
    ver.approved = True
    return ver


def retire_template(name: str) -> TemplateVersion:
    """Mark the latest version of ``name`` as retired."""

    ver = get_latest_template(name)
    if not ver:
        raise ValueError("template not found")
    ver.retired = True
    return ver


def get_latest_template(name: str) -> TemplateVersion | None:
    """Return the most recent template for ``name`` if it exists."""

    versions = _template_store.get(name)
    if not versions:
        return None
    return versions[-1]


def list_template_versions(name: str) -> List[TemplateVersion]:
    """Return all stored versions for ``name``."""

    return list(_template_store.get(name, []))


def list_stored_templates() -> Dict[str, TemplateVersion]:
    """Return the latest version for each stored template."""

    return {name: versions[-1] for name, versions in _template_store.items()}
