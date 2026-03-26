import docreview360.notifications as n
import pytest


def test_send_email_requires_string_recipient():
    with pytest.raises(TypeError):
        n.send_email("default", ["u@example.com"], subject="s", body="b")
