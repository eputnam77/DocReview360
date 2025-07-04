import pytest

from docuflow.ai_utils import create_validated_document


def test_create_validated_document() -> None:
    doc = create_validated_document("f.txt", b"Valid content", user="bob")
    assert doc.content == "Valid content"


def test_invalid_document() -> None:
    with pytest.raises(ValueError):
        create_validated_document("f.txt", b" ")
