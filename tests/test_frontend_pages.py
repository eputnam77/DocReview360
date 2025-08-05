from pathlib import Path


def test_react_pages_exist() -> None:
    # Use robust path resolution relative to the test file location
    pages_dir = Path(__file__).parent.parent / "frontend" / "pages"
    
    for page in [
        "login.tsx",
        "dashboard/index.tsx",
        "editors/word.tsx",
        "projects/new.tsx",
        "editors/tiptap.tsx",
        "viewer.tsx",
        "logs/index.tsx",
    ]:
        assert (pages_dir / page).exists(), f"Page {page} not found"
