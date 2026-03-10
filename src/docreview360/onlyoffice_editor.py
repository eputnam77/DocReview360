# SPDX-License-Identifier: MIT
"""ONLYOFFICE connector."""

from __future__ import annotations


class OnlyofficeConnector:
    """Provide an HTML iframe snippet for a document."""

    def open_document(self, doc_id: str) -> str:
        """Return an iframe snippet pointing to the editor."""
        return f"<iframe src='/onlyoffice/{doc_id}'></iframe>"


__all__ = ["OnlyofficeConnector"]
