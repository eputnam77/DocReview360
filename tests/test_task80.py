from docreview360.documenso import (
    complete_signature,
    request_signature,
    signature_status,
)


def test_sign_document_flow() -> None:
    sig, url, _ = request_signature("doc1", "alice")
    assert url.endswith(sig)
    assert signature_status(sig) == "pending"
    complete_signature(sig)
    assert signature_status(sig) == "signed"
