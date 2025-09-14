import pytest
from docreview360.reporting import throughput_data


def test_throughput_data_requires_positive_days():
    with pytest.raises(ValueError):
        throughput_data(0)
