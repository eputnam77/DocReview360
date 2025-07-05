from pathlib import Path


def test_docs_page_exists() -> None:
    path = Path("docs/tiptap-plugins.md")
    assert path.exists()
    content = path.read_text()
    assert "Plugin Development" in content
