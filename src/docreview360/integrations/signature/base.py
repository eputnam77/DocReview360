from __future__ import annotations

import os
from typing import Any, Dict, Protocol, Tuple

from ...settings_manager import load_settings
from ..registry import get_provider as registry_get_provider
from ..registry import register_provider as registry_register


class SignatureProvider(Protocol):
    """Protocol for e-signature providers."""

    name: str

    def request_signature(
        self,
        document_id: str,
        user: str,
        workflow_id: str | None = None,
        *,
        approval_id: str | None = None,
        return_url: str | None = None,
    ) -> Tuple[str, str, Dict[str, Any]]:
        """Create a signature request and return ``(id, url, metadata)``."""

    def process_webhook(self, data: dict[str, str]) -> None:
        """Handle a webhook payload from the provider."""

    def verify_signature(self, signature_id: str, document: bytes) -> bool:
        """Return ``True`` if ``signature_id`` is valid for ``document``."""

    def validate_signature(
        self,
        document_bytes: bytes,
        certificate_url: str | None,
        metadata: Dict[str, Any],
    ) -> bool:
        """Return ``True`` if ``document_bytes`` matches ``certificate_url``."""


providers: Dict[str, SignatureProvider] = {}


def register_provider(provider: SignatureProvider) -> None:
    """Register ``provider`` with the global registry and local cache."""

    registry_register(provider)
    providers[provider.name] = provider


def get_default_providers() -> list[str]:
    """Return configured signature providers in priority order.

    Environment variables ``SIGNATURE_PROVIDER`` or
    ``SIGNATURE_PROVIDER_PRIMARY`` take precedence for the primary provider
    while ``SIGNATURE_PROVIDER_FALLBACK`` may specify a comma-separated list of
    fallback providers. If neither are set, values are read from the persisted
    settings file with a final fallback to ``["documenso", "local"]``.
    """

    env_primary = os.getenv("SIGNATURE_PROVIDER") or os.getenv("SIGNATURE_PROVIDER_PRIMARY")
    env_fallback = os.getenv("SIGNATURE_PROVIDER_FALLBACK")
    if env_primary or env_fallback:
        providers_list = [env_primary or "documenso"]
        if env_fallback:
            providers_list.extend([p.strip() for p in env_fallback.split(",") if p.strip()])
        return providers_list

    settings = load_settings()
    primary = str(settings.get("signature_provider_primary", "documenso"))
    fallback_setting = settings.get("signature_provider_fallback", "local")
    fallbacks: list[str] = []
    if fallback_setting:
        if isinstance(fallback_setting, str):
            fallbacks = [p.strip() for p in fallback_setting.split(",") if p.strip()]
        else:
            fallbacks = [str(fallback_setting)]
    return [primary, *fallbacks]


def get_default_provider() -> str:
    """Return the configured primary provider."""

    return get_default_providers()[0]


def get_provider(name: str | None = None) -> SignatureProvider:
    if name is not None:
        return registry_get_provider(name)

    for provider_name in get_default_providers():
        try:
            return registry_get_provider(provider_name)
        except KeyError:
            continue
    raise KeyError("no signature provider available")


DEFAULT_PROVIDER = get_default_provider()
