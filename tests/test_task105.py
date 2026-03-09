from pathlib import Path


def test_docs_page_exists() -> None:
    # Use path relative to project root
    project_root = Path(__file__).parent.parent
    path = project_root / "docs" / "tiptap-plugins.md"
    assert path.exists()
    content = path.read_text()
    assert "plugin" in content.lower()
