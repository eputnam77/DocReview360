import pytest

from docreview360.notifications import TEMPLATES, add_template, send_email, sent_emails


def test_add_template_validation() -> None:
    with pytest.raises(ValueError):
        add_template("", "sub", "body")


def test_send_email_validation() -> None:
    TEMPLATES.clear()
    add_template("tmpl", "hi {name}", "hello {name}")
    with pytest.raises(ValueError):
        send_email("tmpl", "", name="x")
    with pytest.raises(KeyError):
        send_email("missing", "user@example.com")
    with pytest.raises(ValueError):
        send_email("tmpl", "user@example.com")

    # success path
    sent_emails.clear()
    email = send_email("tmpl", "u@e", name="Bob")
    assert email["to"] == "u@e"
    assert sent_emails[-1] == email
