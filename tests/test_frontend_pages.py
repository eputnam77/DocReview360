from pathlib import Path


def test_react_pages_exist() -> None:
    for page in ["login.tsx", "dashboard.tsx", "editor.tsx"]:
        assert (Path("frontend/pages") / page).exists()
