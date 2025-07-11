import pytest

from docreview360 import pandiff


def test_compute_diff_validation() -> None:
    with pytest.raises(ValueError):
        pandiff.compute_diff(1, "text")


def test_change_bars() -> None:
    bars = pandiff.change_bars("a\nb", "a\nc")
    assert ("removed", "b") in bars
    assert ("added", "c") in bars
