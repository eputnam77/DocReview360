# SPDX-License-Identifier: MIT
"""Edit RBAC permissions stored in YAML (Task 148)."""

from __future__ import annotations

from pathlib import Path

import yaml

from .yaml_loader import load_yaml_file, save_yaml_file

RBAC_FILE = Path("rbac.yaml")


def load_rbac(path: Path = RBAC_FILE) -> dict[str, dict[str, bool]]:
    """Return RBAC mapping."""
    return load_yaml_file(path, default={}) or {}


def update_permission(role: str, action: str, allowed: bool, path: Path = RBAC_FILE) -> None:
    """Set ``allowed`` for ``role`` and ``action`` and persist."""
    data = load_rbac(path)
    perms = data.setdefault(role, {})
    perms[action] = allowed
    save_yaml_file(path, data)
