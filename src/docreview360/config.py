# SPDX-License-Identifier: MIT
"""Load and save application configuration.

Configuration precedence (highest to lowest)
-------------------------------------------
1. **Environment variables** — ``DOCREVIEW360_<FIELD>`` variables listed in
   ``_ENV_OVERRIDES`` always win, regardless of what the YAML file says.
2. **YAML file** — ``docreview360.yaml`` (path overridable via
   ``DOCREVIEW360_CONFIG_FILE``).  Explicit values in the file take precedence
   over built-in defaults.
3. **Built-in defaults** — defined as default values on the ``Config`` dataclass
   fields.

No module should read environment variables directly; everything must go through
:func:`Config.load` (or :func:`load_with_defaults`) so that the precedence order
is enforced consistently.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .yaml_loader import load_yaml_file, save_yaml_file

_logger = logging.getLogger(__name__)

CONFIG_FILE = Path(os.getenv("DOCREVIEW360_CONFIG_FILE", "docreview360.yaml"))

# Mapping: Config field name → environment variable name.
# Env vars in this table always override the corresponding YAML value.
_ENV_OVERRIDES: dict[str, str] = {
    "database": "DOCREVIEW360_DATABASE",
    "editor": "DOCREVIEW360_EDITOR",
    "cms": "DOCREVIEW360_CMS",
    "auth": "DOCREVIEW360_AUTH",
    "database_url": "DOCREVIEW360_DATABASE_URL",
    "host": "DOCREVIEW360_HOST",
    "debug": "DOCREVIEW360_DEBUG",
    "inactivity_timeout_minutes": "DOCREVIEW360_INACTIVITY_TIMEOUT",
    "branding_company_name": "DOCREVIEW360_BRANDING_COMPANY_NAME",
    "branding_logo_url": "DOCREVIEW360_BRANDING_LOGO_URL",
    "federal_style_validator_url": "FEDERAL_STYLE_VALIDATOR_URL",
    "search_backend": "DOCREVIEW360_SEARCH_BACKEND",
    "opensearch_url": "OPENSEARCH_URL",
    "elasticsearch_url": "ELASTICSEARCH_URL",
}
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
    # Base URL of a running Federal Style Validator (FSV) instance.
    # When set, DocReview360 proxies style/quality/regulatory checks to FSV
    # instead of running internal implementations.  Example:
    #   FEDERAL_STYLE_VALIDATOR_URL=http://fsv-service:8080
    # Leave unset (None) to continue using the built-in internal checks.
    federal_style_validator_url: str | None = None
    # Full-text search backend.
    # "sqlite"       — built-in SQLite FTS (default, no external service needed)
    # "opensearch"   — OpenSearch cluster (requires OPENSEARCH_URL)
    # "elasticsearch"— Elasticsearch cluster (requires ELASTICSEARCH_URL)
    search_backend: str = "sqlite"
    # Base URL for OpenSearch, e.g. "https://localhost:9200".
    # Only used when search_backend="opensearch".
    opensearch_url: str | None = None
    # Base URL for Elasticsearch, e.g. "https://localhost:9200".
    # Only used when search_backend="elasticsearch".
    elasticsearch_url: str | None = None

    @classmethod
    def load(cls, path: Path = CONFIG_FILE) -> "Config | None":
        """Return a ``Config`` loaded from ``path`` or ``None`` if missing."""
        if not path.exists():
            return None
        _normalized_environment()
        raw = load_yaml_file(path, default={}) or {}
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
        # Apply env var overrides (highest precedence tier).
        cfg._apply_env_overrides()
        if cfg.debug and _is_production_environment():
            raise ValueError("debug must be disabled when DOCREVIEW360_ENV is production-like")
        return cfg

    def _apply_env_overrides(self) -> None:
        """Override YAML-loaded values with environment variable values (in-place).

        This implements the top tier of the configuration precedence hierarchy:
        env var > YAML > built-in default.  Called automatically by :meth:`load`.
        """
        for field_name, env_var in _ENV_OVERRIDES.items():
            raw = os.environ.get(env_var)
            if raw is None:
                continue
            current = getattr(self, field_name, None)
            _logger.debug("Config override via %s: %s=%r (was %r)", env_var, field_name, raw, current)
            # Coerce string env var to the field's Python type.
            if isinstance(current, bool):
                setattr(self, field_name, raw.strip().lower() not in {"0", "false", "no", ""})
            elif isinstance(current, int) or field_name == "inactivity_timeout_minutes":
                try:
                    setattr(self, field_name, int(raw))
                except ValueError:
                    raise ValueError(
                        f"Environment variable {env_var} must be an integer, got {raw!r}"
                    )
            else:
                setattr(self, field_name, raw)

    def validate_startup(self) -> None:
        """Validate required configuration and fail fast with a clear error message.

        Call this once during application startup (e.g. in the lifespan handler)
        so configuration mistakes surface immediately rather than causing
        cryptic runtime failures.

        Raises:
            ValueError: with a list of all validation failures, so operators can
                fix all problems in a single pass.
        """
        errors: list[str] = []

        # Required non-empty string fields.
        for field_name in ("database", "editor", "auth"):
            value = getattr(self, field_name, "")
            if not isinstance(value, str) or not value.strip():
                errors.append(f"  '{field_name}' is required but not set")

        # Port must be a valid TCP port.
        if not (1 <= self.port <= 65535):
            errors.append(f"  'port' must be between 1 and 65535, got {self.port!r}")

        # Inactivity timeout must be positive.
        if self.inactivity_timeout_minutes <= 0:
            errors.append(
                f"  'inactivity_timeout_minutes' must be > 0, got {self.inactivity_timeout_minutes!r}"
            )

        if errors:
            raise ValueError(
                "DocReview360 startup configuration validation failed:\n" + "\n".join(errors)
            )

    def save(self, path: Path = CONFIG_FILE) -> None:
        """Persist this configuration to ``path`` creating directories as needed."""
        path = Path(path)
        try:
            data = {
                k: ([c.__dict__ for c in v] if k == "log_connectors" else v)
                for k, v in self.__dict__.items()
                if v is not None
            }
            save_yaml_file(path, data)
        except OSError as exc:
            raise OSError(f"Failed to write config to {path}") from exc


def load_with_defaults(path: Path = CONFIG_FILE) -> Config:
    """Return a :class:`Config` applying the full precedence hierarchy.

    Precedence (highest → lowest):

    1. Environment variables (``DOCREVIEW360_<FIELD>``).
    2. YAML file at ``path`` (defaults to ``docreview360.yaml``).
    3. Built-in defaults defined on :class:`Config` fields.

    When no YAML file is present the function constructs a ``Config`` from
    built-in defaults and env var overrides only, using sensible values for
    required fields (``database="sqlite"``, ``editor="tiptap"``, ``auth="jwt"``).
    Use :meth:`Config.validate_startup` if you need to enforce that all required
    settings are explicitly provided.
    """
    cfg = Config.load(path)
    if cfg is None:
        # No YAML file — build from built-in defaults then apply env overrides.
        cfg = Config(database="sqlite", editor="tiptap", cms="none", auth="jwt")
        cfg._apply_env_overrides()
    return cfg

