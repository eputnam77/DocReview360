from docuflow.documenso import complete_signature, request_signature, signature_status


def test_sign_document_flow() -> None:
    sig = request_signature("doc1", "alice")
    assert signature_status(sig) == "pending"
    complete_signature(sig)
    assert signature_status(sig) == "signed"
