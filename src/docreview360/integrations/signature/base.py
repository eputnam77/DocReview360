from __future__ import annotations

import os
from typing import Dict, Protocol, Tuple


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

    def process_webhook(self, data: dict) -> None:
        """Handle a webhook payload from the provider."""


providers: Dict[str, SignatureProvider] = {}


def register_provider(provider: SignatureProvider) -> None:
    providers[provider.name] = provider


def get_provider(name: str) -> SignatureProvider:
    return providers[name]


DEFAULT_PROVIDER = os.getenv("SIGNATURE_PROVIDER", "documenso")
