from docuflow import documents
from docuflow.stubs.task22 import task22


def test_task22_sequence() -> None:
    documents._project_document_numbers.clear()
    assert task22("p1") == 1
    assert task22("p1") == 2
    assert task22("p2") == 1
