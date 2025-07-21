import importlib

import pytest


def test_guardrails_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENABLE_GUARDRAILS", "1")
    module = importlib.import_module("docreview360.api")
    importlib.reload(module)
    from docreview360.exporter import guardrails_checker

    assert guardrails_checker is not None
