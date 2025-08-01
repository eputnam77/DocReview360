from pathlib import Path


def test_react_pages_exist() -> None:
    for page in [
        "login.tsx",
        "dashboard/index.tsx",
        "editors/word.tsx",
        "projects/new.tsx",
        "editors/tiptap.tsx",
        "viewer.tsx",
        "logs/index.tsx",
    ]:
        assert (Path("DocReview360/frontend/pages") / page).exists()
