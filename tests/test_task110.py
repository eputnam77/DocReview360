from docuflow.celery_app import quality_gate


def test_quality_gate() -> None:
    score = quality_gate("BAD BAD")
    assert score == 1.0
    score2 = quality_gate("fine text")
    assert score2 == 0.0
