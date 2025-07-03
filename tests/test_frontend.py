import json
from pathlib import Path


def test_frontend_skeleton() -> None:
    pkg_file = Path("frontend/package.json")
    assert pkg_file.exists(), "package.json missing"
    data = json.loads(pkg_file.read_text())
    deps = data.get("dependencies", {})
    assert "react" in deps
    assert "react-dom" in deps
    assert "react-router-dom" in deps

    app_src = Path("frontend/src/App.jsx").read_text()
    assert "BrowserRouter" in app_src
    assert "Route" in app_src
