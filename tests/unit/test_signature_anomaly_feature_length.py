import pytest

from docreview360.ml.features import SIGNATURE_ANOMALY_FEATURE_NAMES
from docreview360.ml.signature_anomaly import score_signature_anomaly


def test_signature_anomaly_feature_length_validation():
    with pytest.raises(ValueError, match="features must contain"):
        score_signature_anomaly([0.0])

    features = [0.0] * len(SIGNATURE_ANOMALY_FEATURE_NAMES)
    score, meta = score_signature_anomaly(features)

    assert 0.0 <= score <= 1.0
    assert meta.sha256
