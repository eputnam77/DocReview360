import pytest

from services.document_checker import detect_anomalies


def test_detect_anomalies_rejects_boolean_threshold() -> None:
    """``threshold`` represents a probability; boolean values are confusing
    because they also act as integers.  Passing ``True`` previously coerced to
    ``1`` which silently changed the comparison logic."""
    with pytest.raises(TypeError):
        detect_anomalies("ok", threshold=True)
