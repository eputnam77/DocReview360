"""Global settings persistence (Task 142)."""

from __future__ import annotations

import base64
import binascii
import os
import warnings
from importlib import import_module, metadata
from pathlib import Path
from typing import Any, Dict

import yaml

from .secrets import configure_vault, store_secret

SETTINGS_FILE = Path(os.getenv("DOCREVIEW360_SETTINGS_FILE", "settings.yaml"))
ENCRYPTED_PREFIX = "ENC("
ENCRYPTED_SUFFIX = ")"


def _is_encrypted_value(value: str) -> bool:
    return value.startswith(ENCRYPTED_PREFIX) and value.endswith(ENCRYPTED_SUFFIX)


def _encode_encrypted_payload(payload: bytes) -> str:
    encoded = base64.b64encode(payload).decode("ascii")
    return f"{ENCRYPTED_PREFIX}{encoded}{ENCRYPTED_SUFFIX}"


def _decode_encrypted_payload(value: str) -> bytes:
    from .crypto import EncryptionError

    if not _is_encrypted_value(value):
        raise EncryptionError("secret payload is not encrypted")
    encoded = value[len(ENCRYPTED_PREFIX) : -len(ENCRYPTED_SUFFIX)]
    if not encoded:
        raise EncryptionError("secret payload is empty")
    try:
        return base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise EncryptionError("secret payload is not valid base64") from exc


def _encrypt_secret_value(secret: str, *, settings: Dict[str, Any]) -> str:
    from .crypto import encrypt_payload

    payload = encrypt_payload(secret.encode("utf-8"), settings=settings)
    return _encode_encrypted_payload(payload)


def _decrypt_secret_value(value: str, *, settings: Dict[str, Any]) -> str:
    from .crypto import decrypt_payload

    payload = _decode_encrypted_payload(value)
    plaintext = decrypt_payload(payload, settings=settings, allow_plaintext=False)
    return plaintext.decode("utf-8")


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
        from .crypto import EncryptionKeyError, should_encrypt_scope

        updated_secrets = dict(secrets_cfg)
        migrated = False
        for name, value in secrets_cfg.items():
            if isinstance(value, str) and value.strip():
                if _is_encrypted_value(value):
                    secret_value = _decrypt_secret_value(value, settings=data)
                else:
                    secret_value = value
                    if should_encrypt_scope("secrets", settings=data):
                        try:
                            updated_secrets[name] = _encrypt_secret_value(
                                secret_value, settings=data
                            )
                        except EncryptionKeyError:
                            warnings.warn(
                                "Plaintext secret found but encryption key material "
                                "is unavailable; cannot migrate secrets to encrypted "
                                "storage."
                            )
                            raise
                        migrated = True
                store_secret(name, secret_value)
        if migrated:
            data["secrets"] = updated_secrets
            path.write_text(yaml.safe_dump(data))
    return data


def update_setting(key: str, value: Any, path: Path = SETTINGS_FILE) -> None:
    """Update a single setting and persist to ``path``."""
    settings = load_settings(path)
    settings[key] = value
    path.write_text(yaml.safe_dump(settings))
    if key == "vault" and isinstance(value, dict):
        configure_vault(value)


def update_secret(provider: str, secret: str | None, path: Path = SETTINGS_FILE) -> None:
    """Persist a secret for ``provider`` inside ``settings.yaml``."""
    if not isinstance(provider, str) or not provider.strip():
        raise ValueError("provider must be a non-empty string")
    settings = load_settings(path)
    from .crypto import should_encrypt_scope

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
        if should_encrypt_scope("secrets", settings=settings):
            secrets_cfg[provider] = _encrypt_secret_value(secret_value, settings=settings)
        else:
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
