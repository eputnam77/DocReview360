"""Ensure vector search handles invalid numeric input."""

import math

import pytest
from docreview360.vector_search import _cosine


def test_cosine_rejects_nan_and_inf() -> None:
    with pytest.raises(ValueError):
        _cosine([1.0, math.nan], [1.0, 0.5])
    with pytest.raises(ValueError):
        _cosine([1.0, 0.5], [1.0, float("inf")])
