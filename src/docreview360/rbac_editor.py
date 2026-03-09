"""Edit RBAC permissions stored in YAML (Task 148)."""

from __future__ import annotations

from pathlib import Path

import yaml


RBAC_FILE = Path("rbac.yaml")


def load_rbac(path: Path = RBAC_FILE) -> dict[str, dict[str, bool]]:
    """Return RBAC mapping."""
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def update_permission(role: str, action: str, allowed: bool, path: Path = RBAC_FILE) -> None:
    """Set ``allowed`` for ``role`` and ``action`` and persist."""
    data = load_rbac(path)
    perms = data.setdefault(role, {})
    perms[action] = allowed
    path.write_text(yaml.safe_dump(data))
