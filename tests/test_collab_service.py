import pytest
from fastapi.testclient import TestClient

from docreview360.api import app
from docreview360.documents import DocumentModel, documents

pytest.importorskip("y_py")
from y_py import YDoc, apply_update, encode_state_as_update


def test_yjs_collaboration_real_time() -> None:
    doc_id = "doc1"
    # Seed empty document
    documents[doc_id] = DocumentModel(id=doc_id, content="")

    client = TestClient(app)

    with (
        client.websocket_connect(f"/collab/{doc_id}") as ws1,
        client.websocket_connect(f"/collab/{doc_id}") as ws2,
    ):
        # Initialize local YDocs with server state
        doc1, doc2 = YDoc(), YDoc()
        apply_update(doc1, ws1.receive_bytes())
        apply_update(doc2, ws2.receive_bytes())

        # Client 1 inserts text
        with doc1.begin_transaction() as t:
            doc1.get_text("doc").insert(t, 0, "Hello")
        ws1.send_bytes(encode_state_as_update(doc1))
        update = ws2.receive_bytes()
        apply_update(doc2, update)
        assert str(doc2.get_text("doc")) == "Hello"

        # Client 2 appends more text
        with doc2.begin_transaction() as t:
            doc2.get_text("doc").insert(t, 5, " World")
        ws2.send_bytes(encode_state_as_update(doc2))
        update2 = ws1.receive_bytes()
        apply_update(doc1, update2)

        assert str(doc1.get_text("doc")) == "Hello World"
        assert str(doc1.get_text("doc")) == str(doc2.get_text("doc"))

    # Ensure updates were persisted for reconciliation
    assert documents[doc_id].history[-1].yjs_updates is not None
    documents.pop(doc_id, None)
