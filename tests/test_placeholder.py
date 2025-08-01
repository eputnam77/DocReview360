import pytest
from docreview360 import placeholder


def test_placeholder_default() -> None:
    assert placeholder() == 42


def test_placeholder_multiplier() -> None:
    assert placeholder(2) == 84


def test_placeholder_negative() -> None:
    with pytest.raises(ValueError):
        placeholder(-1)
