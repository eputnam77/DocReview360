import json
from pathlib import Path


def test_state_management_setup() -> None:
    # Use paths relative to project root
    project_root = Path(__file__).parent.parent
    pkg = json.loads((project_root / "frontend" / "package.json").read_text())
    deps = pkg.get("dependencies", {})
    assert "@tanstack/react-query" in deps
    assert "zustand" in deps

    app_src = (project_root / "frontend" / "pages" / "_app.tsx").read_text()
    assert "QueryClientProvider" in app_src

    store_src = (project_root / "frontend" / "state" / "useStore.ts").read_text()
    assert "useCounterStore" in store_src
