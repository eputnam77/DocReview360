# SPDX-License-Identifier: MIT
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ProviderInfo:
    """Metadata wrapper for an integration provider."""

    provider: Any
    metadata: Dict[str, Any] = field(default_factory=dict)


_providers: Dict[str, ProviderInfo] = {}

_logger = logging.getLogger(__name__)


def register_provider(
    provider: Any,
    *,
    name: str | None = None,
    metadata: Dict[str, Any] | None = None,
) -> None:
    """Register ``provider`` under ``name`` with optional ``metadata``."""

    provider_name = name or getattr(provider, "name", None)
    if not provider_name:
        raise ValueError("provider must define a non-empty 'name'")
    _providers[provider_name] = ProviderInfo(provider, metadata or {})


def get_provider(name: str) -> Any:
    """Return the provider registered as ``name``."""

    return _providers[name].provider


def providers() -> Dict[str, ProviderInfo]:
    """Return a copy of the full provider registry.

    Returning the internal dictionary previously exposed the registry to
    accidental external mutation.  Callers modifying the returned mapping would
    inadvertently affect global state.  Returning a shallow copy prevents this
    class of bugs while keeping the API simple.
    """

    return dict(_providers)


def provider_names() -> List[str]:
    """List registered provider names."""

    return list(_providers)


# Automatically load providers from entry points or config when this module is imported.
try:  # pragma: no cover - best effort loading
    from .. import settings_manager as _settings

    _settings.load_providers()
except Exception as exc:  # pragma: no cover - no action on failure
    _logger.warning("Failed to load integration providers: %s", exc)
