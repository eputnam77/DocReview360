from docreview360.documents import DocumentModel
from docreview360.editor_switcher import render_editor


def test_render_editor_handles_whitespace_and_case() -> None:
    doc = DocumentModel(id="1", content="hello", editor=" OnlyOffice ")
    html = render_editor(doc)
    assert "/onlyoffice/" in html
