import pytest

from docreview360.toast_editor import ToastEditor


def test_toast_editor_open() -> None:
    ed = ToastEditor()
    html = ed.open_document("xyz")
    assert "toast-editor" in html


def test_toast_editor_requires_id() -> None:
    ed = ToastEditor()
    with pytest.raises(ValueError):
        ed.open_document("")
