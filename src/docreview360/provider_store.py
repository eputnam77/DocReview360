# SPDX-License-Identifier: MIT
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .yaml_loader import load_yaml_file, save_yaml_file

# Default location for provider configuration
# Default path for provider configuration.  The value is intentionally kept
# mutable so tests can monkeypatch :data:`PROVIDERS_FILE` and have subsequent
# helper functions pick up the change.  Using a module level variable avoids
# freezing the path at function definition time.
PROVIDERS_FILE = Path("providers.yaml")

# Default providers shipped with the application. These defaults prioritise
# ``documenso`` for cloud signing, keep the built-in ``sandbox`` provider as a
# local development fallback, and retain ``local`` as the final escape hatch.
DEFAULT_PROVIDERS: Dict[str, Dict[str, Any]] = {
    "documenso": {"api_key": "", "priority": 1, "healthy": True},
    "sandbox": {"api_key": "", "priority": 5, "healthy": True},
    "local": {"api_key": "", "priority": 10, "healthy": True},
}


def load_providers(path: Path | None = None) -> Dict[str, Dict[str, Any]]:
    """Return provider configuration.

    Parameters
    ----------
    path:
        Optional location of the provider configuration file.  When ``None``
        (the default) the current value of :data:`PROVIDERS_FILE` is used.  This
        indirection allows tests to monkeypatch ``PROVIDERS_FILE`` after import
        without the default argument capturing the original path.

    If ``path`` does not exist an in-memory copy of :data:`DEFAULT_PROVIDERS`
    is returned so tests can operate without touching the real filesystem.
    """

    path = path or PROVIDERS_FILE
    if not path.exists():
        return {k: v.copy() for k, v in DEFAULT_PROVIDERS.items()}
    data = load_yaml_file(path, default={}) or {}
    if not isinstance(data, dict):
        raise ValueError("providers file must contain a mapping")
    # Each provider definition must itself be a mapping so callers do not end up
    # with unexpected primitive values which would later break lookups in
    # :func:`get_active_providers`.  Previously a value such as ``"documenso:
    # invalid"`` would be accepted and propagated as a plain string, leading to
    # attribute errors when accessed as a mapping.  Validate eagerly and raise a
    # helpful error instead.
    for name, cfg in list(data.items()):
        if not isinstance(cfg, dict):
            raise ValueError(f"configuration for provider '{name}' must be a mapping")
        default_cfg = DEFAULT_PROVIDERS.get(name, {})
        raw_priority = cfg.get("priority", default_cfg.get("priority", 100))
        try:
            if isinstance(raw_priority, bool):
                raise TypeError
            priority = int(raw_priority)
        except (TypeError, ValueError):
            priority = int(default_cfg.get("priority", 100))
        if priority <= 0:
            priority = int(default_cfg.get("priority", 100))
        cfg["priority"] = priority
        raw_healthy = cfg.get("healthy", default_cfg.get("healthy", True))
        cfg["healthy"] = raw_healthy if isinstance(raw_healthy, bool) else True
    # ensure expected structure and defaults
    for name, cfg in DEFAULT_PROVIDERS.items():
        data.setdefault(name, cfg.copy())
    return data


def save_providers(providers: Dict[str, Dict[str, Any]], path: Path | None = None) -> None:
    """Persist ``providers`` mapping to ``path``."""

    path = path or PROVIDERS_FILE
    save_yaml_file(path, providers)


def get_active_providers(path: Path | None = None) -> List[str]:
    """Return provider names sorted by priority and filtered by health."""

    providers = load_providers(path)
    ordered = sorted(providers.items(), key=lambda kv: kv[1].get("priority", 100))
    return [name for name, cfg in ordered if cfg.get("healthy", True)]


def set_provider_health(name: str, healthy: bool, path: Path | None = None) -> None:
    """Update health status for ``name`` and persist it."""

    providers = load_providers(path)
    cfg = providers.setdefault(name, {"api_key": "", "priority": 100, "healthy": True})
    cfg["healthy"] = healthy
    save_providers(providers, path)
