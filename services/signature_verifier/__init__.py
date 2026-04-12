# SPDX-License-Identifier: MIT
"""Compatibility wrapper for the packaged signature verifier."""

from docreview360.services.signature_verifier import (
    schedule_signature_verification,
    verify_document_signatures,
)

__all__ = [
    "schedule_signature_verification",
    "verify_document_signatures",
]
