import pytest

from docreview360.email_templates import TEMPLATES, create_template, update_template


def test_create_template_validates_inputs() -> None:
    TEMPLATES.clear()
    with pytest.raises(TypeError):
        create_template("tmpl1", 123, "body")
    with pytest.raises(TypeError):
        create_template("tmpl2", "subject", 123)
    with pytest.raises(TypeError):
        create_template("tmpl3", "subject", "body", task=123)
    with pytest.raises(ValueError):
        create_template("   ", "subject", "body")
    with pytest.raises(ValueError):
        create_template("tmpl4", "", "body")
    with pytest.raises(ValueError):
        create_template("tmpl5", "sub", " ")


def test_update_template_rejects_blank_values() -> None:
    TEMPLATES.clear()
    create_template("t1", "sub", "body")
    with pytest.raises(ValueError):
        update_template("t1", subject=" ")
    with pytest.raises(ValueError):
        update_template("t1", body="")
