from docreview360.onlyoffice_editor import OnlyofficeConnector


def test_open_document() -> None:
    conn = OnlyofficeConnector()
    iframe = conn.open_document("123")
    assert "onlyoffice/123" in iframe
