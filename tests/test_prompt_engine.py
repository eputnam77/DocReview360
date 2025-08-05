import pytest

import docreview360.ai_utils as ai


def test_render_prompt() -> None:
    ai.add_prompt_template("hello", "Hi {person}")
    assert ai.render_prompt("hello", person="Bob") == "Hi Bob"


def test_synth_compress(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ai, "synth_enabled", True)
    result = ai.synth_compress("This is a test")
    assert result == "Ths tst"


def test_suggest_export_format() -> None:
    assert ai.suggest_export_format("an image here") == "pdf"
    assert ai.suggest_export_format("data table included") == "xlsx"
