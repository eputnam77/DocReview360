"""Global settings persistence (Task 142)."""

from __future__ import annotations

from importlib import import_module, metadata
from pathlib import Path
from typing import Any, Dict

import yaml

from .secrets import configure_vault, store_secret
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
    secrets_cfg = data.get("secrets")
    if isinstance(secrets_cfg, dict):
        for name, value in secrets_cfg.items():
            if isinstance(value, str) and value.strip():
                store_secret(name, value)
    return data


def update_setting(key: str, value: Any, path: Path = SETTINGS_FILE) -> None:
    """Update a single setting and persist to ``path``."""
    settings = load_settings(path)
    settings[key] = value
    path.write_text(yaml.safe_dump(settings))
    if key == "vault" and isinstance(value, dict):
        configure_vault(value)
    record_task_completion(142)


def update_secret(provider: str, secret: str | None, path: Path = SETTINGS_FILE) -> None:
    """Persist a secret for ``provider`` inside ``settings.yaml``."""
    if not isinstance(provider, str) or not provider.strip():
        raise ValueError("provider must be a non-empty string")
    settings = load_settings(path)
    secrets_cfg = settings.get("secrets")
    if secrets_cfg is None:
        secrets_cfg = {}
    if not isinstance(secrets_cfg, dict):
        raise ValueError("secrets must be a mapping")
    if secret is None or not str(secret).strip():
        secrets_cfg.pop(provider, None)
        secret_value = None
    else:
        secret_value = str(secret)
        secrets_cfg[provider] = secret_value
    settings["secrets"] = secrets_cfg
    path.write_text(yaml.safe_dump(settings))
    try:
        from . import ai_assist
    except Exception:
        ai_assist = None
    if ai_assist is not None:
        ai_assist.OPENAI_KEY = secret_value
    if secret_value:
        store_secret(provider, secret_value)


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
