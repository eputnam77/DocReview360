# SPDX-License-Identifier: MIT
"""Unit tests for src/docreview360/pagination.py (Item 50 Phase 2)."""

from __future__ import annotations


def test_paginated_response_basic() -> None:
    from docreview360.pagination import PaginatedResponse

    seq = list(range(100))
    page = PaginatedResponse.from_sequence(seq, skip=0, limit=20)
    assert page.total == 100
    assert page.skip == 0
    assert page.limit == 20
    assert page.items == list(range(20))


def test_paginated_response_second_page() -> None:
    from docreview360.pagination import PaginatedResponse

    seq = list(range(100))
    page = PaginatedResponse.from_sequence(seq, skip=20, limit=20)
    assert page.total == 100
    assert page.skip == 20
    assert page.items == list(range(20, 40))


def test_paginated_response_last_partial_page() -> None:
    from docreview360.pagination import PaginatedResponse

    seq = list(range(25))
    page = PaginatedResponse.from_sequence(seq, skip=20, limit=20)
    assert page.total == 25
    assert page.items == [20, 21, 22, 23, 24]


def test_paginated_response_skip_beyond_end() -> None:
    from docreview360.pagination import PaginatedResponse

    seq = [1, 2, 3]
    page = PaginatedResponse.from_sequence(seq, skip=10, limit=5)
    assert page.total == 3
    assert page.items == []


def test_paginated_response_empty_sequence() -> None:
    from docreview360.pagination import PaginatedResponse

    page = PaginatedResponse.from_sequence([], skip=0, limit=20)
    assert page.total == 0
    assert page.items == []


def test_paginated_response_serializes_to_dict() -> None:
    from docreview360.pagination import PaginatedResponse

    page = PaginatedResponse.from_sequence(["a", "b", "c"], skip=0, limit=2)
    data = page.model_dump()
    assert data == {"items": ["a", "b"], "total": 3, "skip": 0, "limit": 2}
