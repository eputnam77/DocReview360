import pytest

from docreview360 import email_templates as et


def setup_function(_):
    et.TEMPLATES.clear()


def test_update_template_can_clear_task():
    et.create_template("welcome", "hi", "body", task="do")
    et.update_template("welcome", task=None)
    assert et.get_template("welcome").task is None


def test_delete_missing_template_raises():
    with pytest.raises(KeyError):
        et.delete_template("missing")
