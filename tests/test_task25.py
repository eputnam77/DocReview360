import os

from docreview360.stubs.task25 import task25


def test_task25_signature_roundtrip() -> None:
    os.environ["DOCREVIEW360_SIGNATURE_SECRET"] = "test-secret"
    assert task25("data") is True
