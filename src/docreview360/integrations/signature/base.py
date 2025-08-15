from __future__ import annotations

import os
from typing import Any, Dict, Protocol, Tuple

from ...settings_manager import load_settings


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
    providers[provider.name] = provider


def get_default_providers() -> Tuple[str, str | None]:
    """Return the configured primary and fallback providers.

    Environment variables ``SIGNATURE_PROVIDER`` or
    ``SIGNATURE_PROVIDER_PRIMARY`` take precedence for the primary provider
    while ``SIGNATURE_PROVIDER_FALLBACK`` overrides the secondary provider.
    If neither are set, values are read from the persisted settings file with
    a final fallback to ``("documenso", "local")``.
    """

    env_primary = os.getenv("SIGNATURE_PROVIDER") or os.getenv("SIGNATURE_PROVIDER_PRIMARY")
    env_fallback = os.getenv("SIGNATURE_PROVIDER_FALLBACK")
    if env_primary or env_fallback:
        return env_primary or "documenso", env_fallback

    settings = load_settings()
    primary = str(settings.get("signature_provider_primary", "documenso"))
    fallback = settings.get("signature_provider_fallback", "local")
    if fallback is not None:
        fallback = str(fallback)
    return primary, fallback


def get_default_provider() -> str:
    """Return the configured primary provider."""

    return get_default_providers()[0]


def get_provider(name: str | None = None) -> SignatureProvider:
    if name is not None:
        return providers[name]

    primary, fallback = get_default_providers()
    try:
        return providers[primary]
    except KeyError:
        if fallback:
            return providers[fallback]
        raise


DEFAULT_PROVIDER = get_default_provider()
