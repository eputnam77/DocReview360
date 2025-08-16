from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml

# Default location for provider configuration
PROVIDERS_FILE = Path("providers.yaml")

# Default providers shipped with the application. These mirror previous
# behaviour which used a primary ``documenso`` provider and a ``local``
# fallback provider.
DEFAULT_PROVIDERS: Dict[str, Dict[str, Any]] = {
    "documenso": {"api_key": "", "priority": 1, "healthy": True},
    "local": {"api_key": "", "priority": 10, "healthy": True},
}


def load_providers(path: Path = PROVIDERS_FILE) -> Dict[str, Dict[str, Any]]:
    """Return provider configuration from ``path``.

    If ``path`` does not exist an in-memory copy of :data:`DEFAULT_PROVIDERS`
    is returned so tests can operate without touching the real filesystem.
    """

    if not path.exists():
        return {k: v.copy() for k, v in DEFAULT_PROVIDERS.items()}
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Invalid YAML in {path}") from exc
    # ensure expected structure and defaults
    for name, cfg in DEFAULT_PROVIDERS.items():
        data.setdefault(name, cfg.copy())
    return data


def save_providers(providers: Dict[str, Dict[str, Any]], path: Path = PROVIDERS_FILE) -> None:
    """Persist ``providers`` mapping to ``path``."""

    path.write_text(yaml.safe_dump(providers))


def get_active_providers(path: Path = PROVIDERS_FILE) -> List[str]:
    """Return provider names sorted by priority and filtered by health."""

    providers = load_providers(path)
    ordered = sorted(providers.items(), key=lambda kv: kv[1].get("priority", 100))
    return [name for name, cfg in ordered if cfg.get("healthy", True)]


def set_provider_health(name: str, healthy: bool, path: Path = PROVIDERS_FILE) -> None:
    """Update health status for ``name`` and persist it."""

    providers = load_providers(path)
    cfg = providers.setdefault(name, {"api_key": "", "priority": 100, "healthy": True})
    cfg["healthy"] = healthy
    save_providers(providers, path)
