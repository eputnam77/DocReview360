from docreview360.celery_app import quality_gate


def test_quality_gate() -> None:
    result = quality_gate("URGENT bad text")
    assert result["blocked"] is True
    assert result["quality"]["score"] < result["thresholds"]["min_quality_score"]

    clean = quality_gate("Routine memo with clear structure")
    assert clean["blocked"] is False
    assert clean["passed"] is True
