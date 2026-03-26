# SPDX-License-Identifier: MIT
"""Property-based tests for pagination helpers (R-15).

Uses Hypothesis to verify invariants that hold for *any* valid input rather
than just the specific examples covered by example-based tests.
"""

from __future__ import annotations

from docreview360.pagination import PaginatedResponse
from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_items = st.lists(st.integers())
_skip = st.integers(min_value=0, max_value=1000)
_limit = st.integers(min_value=1, max_value=500)


# ---------------------------------------------------------------------------
# Invariant tests
# ---------------------------------------------------------------------------


@given(seq=_items, skip=_skip, limit=_limit)
@settings(max_examples=200)
def test_total_always_equals_len_of_input(seq: list[int], skip: int, limit: int) -> None:
    """total must always equal len(seq), regardless of skip/limit."""
    result = PaginatedResponse.from_sequence(seq, skip=skip, limit=limit)
    assert result.total == len(seq)


@given(seq=_items, skip=_skip, limit=_limit)
@settings(max_examples=200)
def test_items_length_never_exceeds_limit(seq: list[int], skip: int, limit: int) -> None:
    """The returned page must never be larger than limit."""
    result = PaginatedResponse.from_sequence(seq, skip=skip, limit=limit)
    assert len(result.items) <= limit


@given(seq=_items, skip=_skip, limit=_limit)
@settings(max_examples=200)
def test_skip_and_limit_preserved(seq: list[int], skip: int, limit: int) -> None:
    """The envelope must echo back the same skip/limit values it received."""
    result = PaginatedResponse.from_sequence(seq, skip=skip, limit=limit)
    assert result.skip == skip
    assert result.limit == limit


@given(seq=_items, skip=_skip, limit=_limit)
@settings(max_examples=200)
def test_items_is_subset_of_input(seq: list[int], skip: int, limit: int) -> None:
    """Every returned item must exist in the original sequence."""
    result = PaginatedResponse.from_sequence(seq, skip=skip, limit=limit)
    for item in result.items:
        assert item in seq


@given(seq=_items, skip=_skip, limit=_limit)
@settings(max_examples=200)
def test_empty_result_when_skip_exceeds_total(seq: list[int], skip: int, limit: int) -> None:
    """When skip >= total the page must be empty."""
    result = PaginatedResponse.from_sequence(seq, skip=skip, limit=limit)
    if skip >= len(seq):
        assert result.items == []


@given(seq=_items)
@settings(max_examples=100)
def test_full_page_with_skip_zero_and_large_limit(seq: list[int]) -> None:
    """skip=0 and limit >= len(seq) must return all items."""
    result = PaginatedResponse.from_sequence(seq, skip=0, limit=max(len(seq), 1))
    assert result.items == seq
