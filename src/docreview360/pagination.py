# SPDX-License-Identifier: MIT
"""Shared pagination helpers for iOS-companion API (Item 50 Phase 2).

All paginated list endpoints use :class:`PaginatedResponse` as their envelope:

.. code-block:: json

    {
        "items": [...],
        "total": 42,
        "skip": 0,
        "limit": 20
    }
"""

from __future__ import annotations

from typing import Any, Generic, Sequence, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated envelope used by all iOS-companion list endpoints."""

    items: list[Any]
    total: int
    skip: int
    limit: int

    @classmethod
    def from_sequence(
        cls,
        seq: Sequence[Any],
        *,
        skip: int,
        limit: int,
    ) -> "PaginatedResponse":
        """Slice *seq* and wrap in the envelope.

        Args:
            seq:    The full (unsliced) sequence returned by the data layer.
            skip:   Number of items to skip from the start.
            limit:  Maximum number of items to return.

        Returns:
            A :class:`PaginatedResponse` with ``total`` set to ``len(seq)``
            and ``items`` set to ``seq[skip : skip + limit]``.
        """
        total = len(seq)
        page = list(seq[skip : skip + limit])
        return cls(items=page, total=total, skip=skip, limit=limit)
