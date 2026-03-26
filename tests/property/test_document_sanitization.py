# SPDX-License-Identifier: MIT
"""Property-based tests for document content sanitization (R-15).

Verifies that sanitize_content() upholds safety invariants for arbitrary
text inputs, not just the handful of hand-crafted examples in unit tests.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from docreview360.documents._store import sanitize_content

# Hypothesis strategy for arbitrary printable text
_text = st.text(min_size=0, max_size=2000)


@given(content=_text)
@settings(max_examples=200)
def test_sanitize_never_raises(content: str) -> None:
    """sanitize_content must not raise for any string input."""
    sanitize_content(content)  # should not raise


@given(content=_text)
@settings(max_examples=200)
def test_sanitize_returns_string(content: str) -> None:
    """sanitize_content must always return a str."""
    result = sanitize_content(content)
    assert isinstance(result, str)


@given(content=_text)
@settings(max_examples=200)
def test_sanitize_idempotent(content: str) -> None:
    """Sanitizing twice must produce the same result as sanitizing once."""
    once = sanitize_content(content)
    twice = sanitize_content(once)
    assert once == twice


@given(content=st.text(alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs"))))
@settings(max_examples=200)
def test_plain_text_unchanged(content: str) -> None:
    """Plain alphanumeric text (no HTML) must be returned unchanged."""
    result = sanitize_content(content)
    assert result == content
