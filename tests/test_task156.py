from docreview360.toast_editor import ToastEditor


def test_toast_editor_open() -> None:
    ed = ToastEditor()
    html = ed.open_document("xyz")
    assert "toast-editor" in html
