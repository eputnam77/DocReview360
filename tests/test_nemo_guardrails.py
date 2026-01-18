from docreview360.nemo_guardrails import GuardrailsMiddleware, contains_pii


def test_contains_pii() -> None:
    assert contains_pii("SSN 123-45-6789")
    assert not contains_pii("no sensitive data")


def test_guardrails_handles_sets_and_tuples() -> None:
    mw = GuardrailsMiddleware(lambda r: None, contains_pii)
    assert mw._contains_pii(("a", "123-45-6789"))
    assert mw._contains_pii({"123-45-6789", "b"})
