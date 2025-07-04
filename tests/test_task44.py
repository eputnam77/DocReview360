from docuflow.ai_utils import suggest_export_format


def test_suggest_export_format() -> None:
    assert suggest_export_format("contains image") == "pdf"
    assert suggest_export_format("table data") == "xlsx"
    assert suggest_export_format("plain text") == "markdown"
