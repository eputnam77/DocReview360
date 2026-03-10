# SPDX-License-Identifier: MIT
"""First-run configuration helper (Task 141)."""

from __future__ import annotations

from pathlib import Path

from .config import CONFIG_FILE, Config


def run_setup(
    database: str,
    keycloak_url: str,
    editor: str,
    storage: str,
    bucket: str,
    path: Path | None = None,
) -> Config:
    """Create and save a basic :class:`Config` using wizard values."""

    config = Config(
        database=database,
        editor=editor,
        cms=storage,
        auth=keycloak_url,
    )
    target = path or CONFIG_FILE
    config.save(target)
    return config
