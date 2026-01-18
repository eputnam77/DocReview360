import pytest

from services.document_checker import detect_anomalies


def test_detect_anomalies_threshold_validation() -> None:
    with pytest.raises(ValueError):
        detect_anomalies("text", threshold=-0.1)
    with pytest.raises(ValueError):
        detect_anomalies("text", threshold=1.1)
