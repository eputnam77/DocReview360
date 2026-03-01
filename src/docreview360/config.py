"""Load and save application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

CONFIG_FILE = Path(os.getenv("DOCREVIEW360_CONFIG_FILE", "docreview360.yaml"))
SAFE_DEBUG_ENVS = {"", "dev", "development", "test", "testing"}


def _normalized_environment() -> str:
    """Return normalized runtime environment and enforce explicit production flag."""

    environment = os.getenv("DOCREVIEW360_ENV", "").strip().lower()
    if environment == "prod":
        raise ValueError("DOCREVIEW360_ENV must be set to 'production' for production mode")
    return environment


def _is_production_environment() -> bool:
    """Return ``True`` when the configured runtime environment is production-like."""

    return _normalized_environment() not in SAFE_DEBUG_ENVS


@dataclass
class ConnectorSettings:
    """Settings for an external log connector."""

    type: str
    endpoint: str
    api_key: str | None = None
    batch_size: int = 1


@dataclass
class Config:
    """Configuration options for DocReview360."""

    database: str
    editor: str
    cms: str
    auth: str
    database_url: str | None = None
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    # Toggle for AI auto-assignment of technical writers
    # Disabled by default per request
    ai_auto_assign_writers: bool = False
    # Toggle read logging for confidential data endpoints
    log_reads: bool = True
    # Pattern for exported filenames; placeholders: {id}, {number}
    filename_template: str = "{id}"
    # Global inactivity timeout (minutes) applied to all UI users.
    inactivity_timeout_minutes: int = 30
    # External log connectors configuration
    log_connectors: list["ConnectorSettings"] = field(default_factory=list)
    # Administrator-configurable branding shown in the UI.
    branding_company_name: str = "DocReview360"
    branding_logo_url: str | None = None
    branding_logo_alt: str = "Organization logo"
    branding_support_url: str = "/docs/"
    branding_docs_url: str = "/docs/"
    branding_security_url: str = "/security"
    branding_privacy_url: str = "/privacy"

    @classmethod
    def load(cls, path: Path = CONFIG_FILE) -> "Config | None":
        """Return a ``Config`` loaded from ``path`` or ``None`` if missing."""
        if not path.exists():
            return None
        _normalized_environment()
        try:
            raw = yaml.safe_load(path.read_text()) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML in {path}") from exc
        if not isinstance(raw, dict):
            raise ValueError(f"Invalid config structure in {path}")
        data: dict[str, Any] = raw
        # YAML 1.1 can coerce "none" to null; normalize to string to satisfy
        # required config fields downstream.
        if data.get("cms") is None:
            data["cms"] = "none"
        if "database_url" not in data:
            data["database_url"] = None
        connectors_raw = data.pop("log_connectors", []) or []
        if not isinstance(connectors_raw, list):
            raise ValueError("log_connectors must be a list")
        connectors = []
        for c in connectors_raw:
            if not isinstance(c, dict):
                raise ValueError("log_connectors entries must be objects")
            normalized = dict(c)
            if "batch_size" in normalized:
                raw_batch = normalized.get("batch_size", 1)
                try:
                    if isinstance(raw_batch, bool):
                        raise TypeError
                    batch = int(raw_batch)
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        "log_connectors batch_size must be a positive integer"
                    ) from exc
                if batch <= 0:
                    raise ValueError("log_connectors batch_size must be a positive integer")
                normalized["batch_size"] = batch
            connectors.append(ConnectorSettings(**normalized))
        data["log_connectors"] = connectors
        raw_timeout = data.get("inactivity_timeout_minutes")
        if raw_timeout is not None:
            try:
                if isinstance(raw_timeout, bool):
                    raise TypeError
                timeout_value = int(raw_timeout)
            except (TypeError, ValueError) as exc:
                raise ValueError("inactivity_timeout_minutes must be a positive integer") from exc
            if timeout_value <= 0:
                raise ValueError("inactivity_timeout_minutes must be a positive integer")
            data["inactivity_timeout_minutes"] = timeout_value
        branding_name = str(data.get("branding_company_name") or "").strip()
        data["branding_company_name"] = branding_name or "DocReview360"
        branding_alt = str(data.get("branding_logo_alt") or "").strip()
        data["branding_logo_alt"] = branding_alt or "Organization logo"
        for link_key, link_default in (
            ("branding_support_url", "/docs/"),
            ("branding_docs_url", "/docs/"),
            ("branding_security_url", "/security"),
            ("branding_privacy_url", "/privacy"),
        ):
            link_value = str(data.get(link_key) or "").strip()
            data[link_key] = link_value or link_default
        cfg = cls(**data)
        if cfg.debug and _is_production_environment():
            raise ValueError("debug must be disabled when DOCREVIEW360_ENV is production-like")
        return cfg

    def save(self, path: Path = CONFIG_FILE) -> None:
        """Persist this configuration to ``path`` creating directories as needed."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = {
                k: ([c.__dict__ for c in v] if k == "log_connectors" else v)
                for k, v in self.__dict__.items()
                if v is not None
            }
            path.write_text(yaml.safe_dump(data))
        except OSError as exc:
            raise OSError(f"Failed to write config to {path}") from exc

