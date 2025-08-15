from __future__ import annotations

import os
from typing import Dict, Protocol, Tuple

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
    ) -> Tuple[str, str]:
        """Create a signature request and return ``(id, url)``."""

    def process_webhook(self, data: dict[str, str]) -> None:
        """Handle a webhook payload from the provider."""

    def verify_signature(self, signature_id: str, document: bytes) -> bool:
        """Return ``True`` if ``signature_id`` is valid for ``document``."""


providers: Dict[str, SignatureProvider] = {}


def register_provider(provider: SignatureProvider) -> None:
    providers[provider.name] = provider


def get_default_provider() -> str:
    """Return the active provider name.

    Environment variable ``SIGNATURE_PROVIDER`` takes precedence. If unset,
    the value is read from the persisted settings file. Falling back to
    ``"documenso"`` keeps previous behaviour when no configuration exists.
    """

    env = os.getenv("SIGNATURE_PROVIDER")
    if env:
        return env
    settings = load_settings()
    return str(settings.get("signature_provider", "documenso"))


def get_provider(name: str | None = None) -> SignatureProvider:
    if name is None:
        name = get_default_provider()
    return providers[name]


DEFAULT_PROVIDER = get_default_provider()
