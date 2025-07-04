from docuflow.stubs.task80 import sign_document


def test_sign_document() -> None:
    sig = sign_document("doc1", "alice")
    assert sig == "signature:doc1:alice"
