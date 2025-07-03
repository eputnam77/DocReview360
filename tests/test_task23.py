from docuflow.stubs.task23 import task23


def test_task23_assistance() -> None:
    doc_type, valid = task23("Monthly report data")
    assert doc_type == "report"
    assert valid
