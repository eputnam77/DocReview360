import pytest

import docreview360.notifications as n


def test_send_email_rejects_whitespace_recipient():
    with pytest.raises(ValueError):
        n.send_email("default", "   ", subject="s", body="b")


def test_send_email_trims_template_name():
    n.sent_emails.clear()
    email = n.send_email(" default ", "user@example.com", subject="s", body="b")
    assert email["subject"] == "s"
