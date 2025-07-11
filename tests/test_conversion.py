from docuflow.conversion import convert_ac_to_order
from docuflow.documents import DocumentModel


def test_convert_ac_to_order() -> None:
    doc = DocumentModel(id="d1", content="Advisory Circular AC-123 test")
    converted = convert_ac_to_order(doc)
    assert "Order" in converted.content
    assert "ORD-123" in converted.content
