from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ProviderInfo:
    """Metadata wrapper for an integration provider."""

    provider: Any
    metadata: Dict[str, Any] = field(default_factory=dict)


_providers: Dict[str, ProviderInfo] = {}


def register_provider(
    provider: Any,
    *,
    name: str | None = None,
    metadata: Dict[str, Any] | None = None,
) -> None:
    """Register ``provider`` under ``name`` with optional ``metadata``."""

    provider_name = name or getattr(provider, "name", None)
    if provider_name is None:
        raise ValueError("provider must define a 'name'")
    _providers[provider_name] = ProviderInfo(provider, metadata or {})


def get_provider(name: str) -> Any:
    """Return the provider registered as ``name``."""

    return _providers[name].provider


def providers() -> Dict[str, ProviderInfo]:
    """Return the full provider registry."""

    return _providers


def provider_names() -> List[str]:
    """List registered provider names."""

    return list(_providers)


# Automatically load providers from entry points or config when this module is imported.
try:  # pragma: no cover - best effort loading
    from .. import settings_manager as _settings

    _settings.load_providers()
except Exception:  # pragma: no cover - no action on failure
    pass
