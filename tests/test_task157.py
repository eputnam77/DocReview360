from docreview360.xml_editor import XMLEditor


def test_xml_editor_open() -> None:
    ed = XMLEditor()
    html = ed.open_document("abc")
    assert "xml-editor" in html
