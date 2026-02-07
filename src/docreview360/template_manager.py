"""Manage golden Markdown templates (Task 143)."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import os
from base64 import b64decode, b64encode
from pathlib import Path
from typing import Any, Dict, List

from filelock import FileLock

from .stubs import record_task_completion

TEMPLATES_DIR = Path("templates/golden")
TEMPLATE_STORE_FILE = Path("template_store.json")


def _env_flag_enabled(value: str | None) -> bool:
    """Interpret truthy string values for the persistence feature flag."""

    if value is None:
        return True
    normalized = value.strip().lower()
    return normalized not in {"0", "false", "no", "off"}


DOCREVIEW360_ENABLE_TEMPLATE_PERSISTENCE = _env_flag_enabled(
    os.getenv("DOCREVIEW360_ENABLE_TEMPLATE_PERSISTENCE")
)

_ACTIVE_TEMPLATES_FILE: Path = TEMPLATE_STORE_FILE
_TEMPLATES_LOADED: bool = False


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


def _serialize_template_store() -> dict[str, list[dict[str, Any]]]:
    return {
        name: [
            {
                "version": version.version,
                "content": b64encode(version.content).decode("ascii"),
                "metadata": version.metadata,
                "approved": version.approved,
                "retired": version.retired,
            }
            for version in versions
        ]
        for name, versions in _template_store.items()
    }


def _load_template_store() -> None:
    global _TEMPLATES_LOADED
    if _TEMPLATES_LOADED or not DOCREVIEW360_ENABLE_TEMPLATE_PERSISTENCE:
        return
    if not _ACTIVE_TEMPLATES_FILE.exists():
        _TEMPLATES_LOADED = True
        return
    lock = FileLock(f"{_ACTIVE_TEMPLATES_FILE}.lock")
    with lock:
        data = json.loads(_ACTIVE_TEMPLATES_FILE.read_text())
    _template_store.clear()
    for name, versions in data.items():
        parsed_versions = []
        for entry in versions:
            parsed_versions.append(
                TemplateVersion(
                    version=entry["version"],
                    content=b64decode(entry["content"]),
                    metadata=entry.get("metadata", {}),
                    approved=entry.get("approved", False),
                    retired=entry.get("retired", False),
                )
            )
        _template_store[name] = parsed_versions
    _TEMPLATES_LOADED = True


def _save_template_store() -> None:
    if not DOCREVIEW360_ENABLE_TEMPLATE_PERSISTENCE:
        return
    _ACTIVE_TEMPLATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(f"{_ACTIVE_TEMPLATES_FILE}.lock")
    with lock:
        _ACTIVE_TEMPLATES_FILE.write_text(json.dumps(_serialize_template_store(), indent=2))


def reset_template_store(keep_file: bool = False, root: Path | None = None) -> None:
    """Reset the in-memory store and optionally remove the persisted file."""
    global _TEMPLATES_LOADED, _ACTIVE_TEMPLATES_FILE

    if root is not None:
        _ACTIVE_TEMPLATES_FILE = root
    _template_store.clear()
    _TEMPLATES_LOADED = False
    if not keep_file and _ACTIVE_TEMPLATES_FILE.exists():
        _ACTIVE_TEMPLATES_FILE.unlink()
    lock_path = Path(f"{_ACTIVE_TEMPLATES_FILE}.lock")
    if lock_path.exists():
        lock_path.unlink()


def upload_template(
    name: str, data: bytes, metadata: Dict[str, Any] | None = None
) -> TemplateVersion:
    """Store ``data`` and ``metadata`` as a new version for ``name``."""

    _load_template_store()
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
    _save_template_store()
