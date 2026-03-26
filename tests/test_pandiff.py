from typing import cast

import pytest
from docreview360 import pandiff


def test_compute_diff_validation() -> None:
    with pytest.raises(ValueError):
        pandiff.compute_diff(cast(str, 1), "text")


def test_change_bars() -> None:
    bars = pandiff.change_bars("a\nb", "a\nc")
    assert ("removed", "b") in bars
    assert ("added", "c") in bars


def test_change_bars_ignores_hints() -> None:
    """ndiff hint lines should not appear in the result."""
    bars = pandiff.change_bars("spam", "span")
    # Only the removed/added lines should be present; ``?`` hints are skipped.
    assert bars == [("removed", "spam"), ("added", "span")]
