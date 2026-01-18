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


def test_update_template_validates_types():
    et.create_template("demo", "sub", "body")
    with pytest.raises(TypeError):
        et.update_template("demo", subject=123)
    with pytest.raises(TypeError):
        et.update_template("demo", body=object())
    with pytest.raises(TypeError):
        et.update_template("demo", task=123)


def test_delete_template_validates_name() -> None:
    """Deleting templates should validate the provided name."""
    with pytest.raises(ValueError):
        et.delete_template("   ")
    with pytest.raises(TypeError):
        et.delete_template(123)  # type: ignore[arg-type]


def test_get_template_strips_name() -> None:
    et.create_template("alpha", "sub", "body")
    tmpl = et.get_template("  alpha  ")
    assert tmpl is not None and tmpl.name == "alpha"


def test_update_template_strips_name() -> None:
    et.create_template("beta", "sub", "body")
    et.update_template("  beta  ", subject="new")
    assert et.get_template("beta").subject == "new"


def test_delete_template_strips_name() -> None:
    et.create_template("gamma", "sub", "body")
    et.delete_template("  gamma  ")
    assert et.get_template("gamma") is None
