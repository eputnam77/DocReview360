import json
from pathlib import Path


def test_frontend_skeleton() -> None:
    pkg_file = Path("DocReview360/frontend/package.json")
    assert pkg_file.exists(), "package.json missing"
    data = json.loads(pkg_file.read_text())
    deps = data.get("dependencies", {})
    assert "next" in deps
    assert "react" in deps
    assert "react-dom" in deps
    assert "tailwindcss" in deps
    assert "shadcn-ui" in deps
    assert "@tanstack/react-query" in deps
    assert "zustand" in deps

    index_src = Path("DocReview360/frontend/pages/index.tsx").read_text()
    assert "useCounterStore" in index_src
