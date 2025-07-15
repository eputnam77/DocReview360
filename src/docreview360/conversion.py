"""Doc-type conversion helpers."""

from __future__ import annotations

import re

from .documents import DocumentModel


def convert_ac_to_order(doc: DocumentModel) -> DocumentModel:
    """Return a new ``DocumentModel`` converted from AC to Order.

    This helper performs a lightweight transformation replacing
    references to "Advisory Circular" with "Order" and updating
    document identifiers from ``AC-`` to ``ORD-``.  It preserves all
    other fields and history entries.
    """

    content = re.sub(r"Advisory Circular", "Order", doc.content)
    content = re.sub(r"\bAC-(\d+)\b", r"ORD-\1", content)
    converted: DocumentModel = doc.model_copy(deep=True)
    converted.content = content
    return converted
