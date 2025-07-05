import pytest

from docuflow import documenso


def test_documenso_error_handling() -> None:
    with pytest.raises(ValueError):
        documenso.request_signature("", "user")
    sig_id, url = documenso.request_signature("doc1", "user")
    assert url.endswith(sig_id)
    with pytest.raises(KeyError):
        documenso.signature_status("bad")
    documenso.complete_signature(sig_id)
    assert documenso.signature_status(sig_id) == "signed"
