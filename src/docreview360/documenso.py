"""Compatibility wrapper for Documenso provider.

The actual implementation now lives in :mod:`docreview360.integrations.signature.documenso`.
This module re-exports the public functions so existing imports continue to
work.
"""

from .integrations.signature import get_provider
from .integrations.signature.documenso import (
    DOCUMENSO_URL,
    complete_signature,
    process_webhook,
    register_stub_signature,
    request_signature,
)
from .integrations.signature.documenso import (
    signature_status as _doc_signature_status,
)


def signature_status(sig_id: str) -> str:
    """Return the status for ``sig_id`` using the active provider.

    Historically this module always delegated to the Documenso implementation
    which meant tests using the lightweight sandbox provider failed when asking
    for a signature's status.  By consulting the currently active provider we
    ensure the status reflects whichever backend is configured.  Providers that
    do not implement ``signature_status`` fall back to the Documenso stub.
    """

    provider = get_provider()
    provider_status: str | None = None
    if getattr(provider, "name", None) != "documenso" and hasattr(provider, "signature_status"):
        try:
            provider_status = provider.signature_status(sig_id)  # type: ignore[return-value]
        except KeyError:
            provider_status = None
        else:
            if provider_status != "pending":
                return provider_status
    try:
        return _doc_signature_status(sig_id)
    except KeyError:
        if provider_status is not None:
            return provider_status
        if hasattr(provider, "signature_status"):
            return provider.signature_status(sig_id)  # type: ignore[return-value]
        raise


__all__ = [
    "DOCUMENSO_URL",
    "request_signature",
    "complete_signature",
    "signature_status",
    "process_webhook",
    "register_stub_signature",
]
