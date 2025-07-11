from docreview360.codex_editor import CodeXEditor


def test_codex_editor_open() -> None:
    ed = CodeXEditor()
    html = ed.open_document("abc")
    assert "codex-editor" in html
