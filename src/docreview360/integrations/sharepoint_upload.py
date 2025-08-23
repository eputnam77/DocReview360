"""Helpers for uploading finalized documents and metadata to SharePoint."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Callable, Dict

from ..certs import fetch_certificate as _fetch_certificate

SIGNED_FOLDER = os.getenv("SHAREPOINT_SIGNED_FOLDER", "signed")
CERT_FOLDER = os.getenv("SHAREPOINT_CERT_FOLDER", "certificates")


async def upload_final_pdf(
    approval_id: str,
    item_id: str,
    document: bytes | None,
    document_hash: str | None,
    provider_metadata: Dict[str, Any],
    signed_at: datetime,
    *,
    certificate_url: str | None = None,
    fetcher: Callable[[str], bytes] = _fetch_certificate,
) -> None:
    """Upload the finalized ``document`` and related metadata to SharePoint.

    Args:
        approval_id: The approval identifier used to name uploaded artifacts.
        item_id: SharePoint item id to update metadata on.
        document: The finalized PDF bytes.
        document_hash: SHA-256 hash of the document for integrity tracking.
        provider_metadata: Arbitrary metadata returned from the provider such as
            transaction identifiers.
        signed_at: Provider timestamp for when the document was finalized.
        certificate_url: Optional URL to the signing certificate.
    """

    from ..sharepoint import async_client_from_env

    client = await async_client_from_env()

    if document is not None:
        await client.upload_file(f"{SIGNED_FOLDER}/{approval_id}", document)

    cert_bytes = b""
    if certificate_url:
        try:
            cert_bytes = fetcher(certificate_url)
        except Exception:
            cert_bytes = b""
    if cert_bytes:
        await client.upload_file(f"{CERT_FOLDER}/{approval_id}", cert_bytes)

    props = {
        "signedDate": signed_at.isoformat(),
        "certificateUrl": certificate_url or "",
        "documentHash": document_hash or "",
    }

    tx_id = provider_metadata.get("transaction_id") or provider_metadata.get("envelope_id")
    if tx_id:
        props["transactionId"] = str(tx_id)

    ts = provider_metadata.get("timestamp")
    if isinstance(ts, datetime):
        props["providerTimestamp"] = ts.isoformat()
    elif ts is not None:
        props["providerTimestamp"] = str(ts)
    else:
        props["providerTimestamp"] = signed_at.isoformat()

    await client.set_properties(item_id, props)


__all__ = ["upload_final_pdf"]
