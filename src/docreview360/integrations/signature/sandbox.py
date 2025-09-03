"""Sandbox signature provider used for integration tests.

The provider implements the minimal :class:`SignatureProvider` protocol and
stores signature state in memory. Webhook processing is idempotent and does not
perform any network calls which makes it suitable for tests and local
experiments.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple
from uuid import uuid4

from .base import register_provider

_signatures: Dict[str, str] = {}


class SandboxProvider:
    """In-memory signature provider for tests."""

    name = "sandbox"

    def request_signature(
        self,
        document_id: str,
        user: str,
        workflow_id: str | None = None,
        *,
        approval_id: str | None = None,
        return_url: str | None = None,
    ) -> Tuple[str, str, Dict[str, Any]]:
        if not document_id or not user:
            raise ValueError("document_id and user are required")
        sig_id = uuid4().hex
        _signatures[sig_id] = "pending"
        return sig_id, f"/sandbox/{sig_id}", {}

    def process_webhook(self, data: dict[str, str]) -> None:
        sig_id = data.get("id")
        status = data.get("status")
        if not sig_id or status != "signed":
            raise ValueError("invalid payload")
        # Idempotent: setting again to signed is harmless
        _signatures[sig_id] = "signed"

    def signature_status(self, sig_id: str) -> str:
        """Return the current status for ``sig_id``.

        The API expects providers to expose a way to query the state of a
        signature request.  The sandbox provider keeps state in the local
        ``_signatures`` dictionary so we simply look it up and raise ``KeyError``
        when the id is unknown.  This mirrors the behavior of the real
        Documenso implementation and allows repeated webhook deliveries to be
        safely ignored.
        """

        try:
            return _signatures[sig_id]
        except KeyError as exc:  # pragma: no cover - defensive
            raise KeyError(f"Unknown signature id {sig_id}") from exc

    def verify_signature(self, signature_id: str, document: bytes) -> bool:
        return _signatures.get(signature_id) == "signed"

    def validate_signature(
        self,
        document_bytes: bytes,
        certificate_url: str | None,
        metadata: Dict[str, Any],
    ) -> bool:
        return True

    def health_check(self) -> bool:  # pragma: no cover - trivial
        return True


# Register provider on import
register_provider(SandboxProvider())

__all__ = ["SandboxProvider"]
