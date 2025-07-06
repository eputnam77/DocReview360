import base64

import pytest

from docuflow.stubs.task153 import task153


def test_task153_completed() -> None:
    encoded = task153("tok", "https://api")
    decoded = base64.b64decode(encoded).decode()
    assert "DOCUFLOW_TOKEN=tok" in decoded
    assert "DOCUFLOW_API=https://api" in decoded


def test_task153_validation() -> None:
    with pytest.raises(ValueError):
        task153("", "url")
