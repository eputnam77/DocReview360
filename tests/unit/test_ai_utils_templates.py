import pytest
from docreview360 import ai_utils


def test_apply_feedback_template_requires_placeholder():
    with pytest.raises(ValueError):
        ai_utils.apply_feedback_template("no placeholder here", "text")


def test_add_prompt_template_accepts_digits():
    ai_utils.add_prompt_template("greet_digit", "Hello {name1}")
    assert ai_utils.render_prompt("greet_digit", name1="Bob") == "Hello Bob"


def test_render_prompt_missing_context_message():
    ai_utils.add_prompt_template("greet_missing", "Hi {name}")
    with pytest.raises(ValueError) as exc:
        ai_utils.render_prompt("greet_missing")
    assert str(exc.value) == "Missing placeholder in prompt context: name"
