"""Global settings persistence (Task 142)."""

from __future__ import annotations

from importlib import import_module, metadata
from pathlib import Path
from typing import Any, Dict

import yaml

from .secrets import configure_vault
from .stubs import record_task_completion

SETTINGS_FILE = Path("settings.yaml")


def load_settings(path: Path = SETTINGS_FILE) -> Dict[str, Any]:
    """Return settings from ``path`` or an empty mapping."""
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Settings in {path} must be a mapping")
    vault_cfg = data.get("vault")
    if isinstance(vault_cfg, dict):
        configure_vault(vault_cfg)
    return data


def update_setting(key: str, value: Any, path: Path = SETTINGS_FILE) -> None:
    """Update a single setting and persist to ``path``."""
    settings = load_settings(path)
    settings[key] = value
    path.write_text(yaml.safe_dump(settings))
    if key == "vault" and isinstance(value, dict):
        configure_vault(value)
    record_task_completion(142)


def load_providers() -> None:
    """Import provider integrations via entry points or configuration.

    Entry points under the ``docreview360.providers`` group are loaded and
    registered with the global provider registry.  In addition, any modules
    listed in the ``provider_modules`` setting are imported which allows them
    to register providers as a side effect.
    """

    from .integrations.registry import register_provider

    for ep in metadata.entry_points().select(group="docreview360.providers"):
        try:
            provider = ep.load()
        except Exception:
            continue
        name = getattr(provider, "name", ep.name)
        register_provider(provider, name=name)

    settings = load_settings()
    modules = settings.get("provider_modules", [])
    if not isinstance(modules, list):
        raise ValueError("provider_modules must be a list")
    for mod in modules:
        if not isinstance(mod, str) or not mod.strip():
            raise ValueError("provider_modules entries must be non-empty strings")
        try:
            import_module(str(mod))
        except Exception:
            continue
