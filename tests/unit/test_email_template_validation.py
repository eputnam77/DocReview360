import pytest

from docreview360 import email_templates


def test_create_template_validates_inputs(tmp_path) -> None:
    email_templates.reset_email_templates(root=tmp_path / "email_templates.json")
    with pytest.raises(TypeError):
        email_templates.create_template("tmpl1", 123, "body")
    with pytest.raises(TypeError):
        email_templates.create_template("tmpl2", "subject", 123)
    with pytest.raises(TypeError):
        email_templates.create_template("tmpl3", "subject", "body", task=123)
    with pytest.raises(ValueError):
        email_templates.create_template("   ", "subject", "body")
    with pytest.raises(ValueError):
        email_templates.create_template("tmpl4", "", "body")
    with pytest.raises(ValueError):
        email_templates.create_template("tmpl5", "sub", " ")


def test_update_template_rejects_blank_values(tmp_path) -> None:
    email_templates.reset_email_templates(root=tmp_path / "email_templates.json")
    email_templates.create_template("t1", "sub", "body")
    with pytest.raises(ValueError):
        email_templates.update_template("t1", subject=" ")
    with pytest.raises(ValueError):
        email_templates.update_template("t1", body="")
