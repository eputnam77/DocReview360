import json
from pathlib import Path


def test_frontend_skeleton() -> None:
    # Use robust path resolution relative to the test file location
    pkg_file = Path(__file__).parent.parent / "frontend" / "package.json"
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

    index_src = (Path(__file__).parent.parent / "frontend" / "pages" / "index.tsx").read_text()
    # The home page should ping the API and redirect to login
    assert "/ping" in index_src
    assert 'router.push("/login")' in index_src
