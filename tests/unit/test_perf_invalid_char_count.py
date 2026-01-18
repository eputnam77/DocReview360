import pytest

from docreview360.perf import measure_typing_time


def test_measure_typing_time_rejects_non_positive() -> None:
    with pytest.raises(ValueError):
        measure_typing_time(0)
