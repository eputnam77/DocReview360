from docreview360.stubs.task79 import OnlyofficeConnector


def test_open_document() -> None:
    conn = OnlyofficeConnector()
    iframe = conn.open_document("123")
    assert "onlyoffice/123" in iframe
