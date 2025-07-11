from docreview360.nemo_guardrails import contains_pii


def test_contains_pii() -> None:
    assert contains_pii("SSN 123-45-6789")
    assert not contains_pii("no sensitive data")
