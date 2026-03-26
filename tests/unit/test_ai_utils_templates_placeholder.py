import pytest
from docreview360.ai_utils import add_feedback_template, apply_feedback_template


def test_add_feedback_template_requires_placeholder():
    with pytest.raises(ValueError):
        add_feedback_template("bad", "{{text}}")


def test_apply_feedback_template_rejects_escaped_placeholder():
    with pytest.raises(ValueError):
        apply_feedback_template("{{text}}", "content")
