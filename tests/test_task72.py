from docreview360.ai_utils import detect_anomalies


def test_anomaly_detection() -> None:
    assert detect_anomalies("normal text") is False
    assert detect_anomalies("bad bad text") is True
