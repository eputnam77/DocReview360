import pytest

from docuflow.stubs.task152 import task152


def test_task152_small_diff() -> None:
    assert task152("old", "new") == "new"


def test_task152_large_diff() -> None:
    current = "\n".join(["a"] * 10)
    latest = "\n".join(["b"] * 20)
    with pytest.raises(ValueError):
        task152(current, latest)
