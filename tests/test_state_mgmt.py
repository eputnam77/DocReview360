import json
from pathlib import Path


def test_state_management_setup() -> None:
    pkg = json.loads(Path("frontend/package.json").read_text())
    deps = pkg.get("dependencies", {})
    assert "@tanstack/react-query" in deps
    assert "zustand" in deps

    app_src = Path("frontend/pages/_app.tsx").read_text()
    assert "QueryClientProvider" in app_src

    store_src = Path("frontend/state/useStore.ts").read_text()
    assert "useCounterStore" in store_src
