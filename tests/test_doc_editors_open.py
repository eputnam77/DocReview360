from pathlib import Path

from docreview360.documents import DocumentModel
from docreview360.editor_switcher import render_editor
from docreview360.onlyoffice_editor import OnlyofficeConnector


def test_all_editors_open() -> None:
    doc = DocumentModel(id="1", content="hi")
    assert "tiptap-editor" in render_editor(doc)
    assert "tiptap-editor" in render_editor(DocumentModel(id="3", content="hi", editor="tiptap"))
    assert "ckeditor5-editor" in render_editor(
        DocumentModel(id="2", content="hi", editor="ckeditor5")
    )
    assert "onlyoffice/1" in OnlyofficeConnector().open_document("1")


def test_tiptap_extension_files() -> None:
    base = Path("frontend/extensions")
    files = [
        "tiptapHeadingLock.ts",
        "tiptapIndentation.ts",
        "tiptapSectionNode.ts",
        "tiptapWatermark.ts",
        "tiptapMarkReview.ts",
        "tiptapYjsCollab.ts",
        "tiptapStructure.ts",
        "tiptapSlashCommand.tsx",
    ]
    for name in files:
        fp = base / name
        assert fp.exists(), f"missing {name}"
        text = fp.read_text()
        assert "export" in text
