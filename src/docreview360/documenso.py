"""Compatibility wrapper for Documenso provider.

The actual implementation now lives in :mod:`docreview360.integrations.signature.documenso`.
This module re-exports the public functions so existing imports continue to
work.
"""

from .integrations.signature.documenso import (  # noqa: F401
    DOCUMENSO_URL,
    complete_signature,
    process_webhook,
    request_signature,
    signature_status,
)

__all__ = [
    "DOCUMENSO_URL",
    "request_signature",
    "complete_signature",
    "signature_status",
    "process_webhook",
]
