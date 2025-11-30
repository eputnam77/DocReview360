"""Command-line helper to regenerate ML golden fixtures used in tests."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    ROOT = Path(__file__).resolve().parents[1]
    SRC = ROOT / "src"
    for candidate in (str(SRC), str(ROOT)):
        if candidate not in sys.path:
            sys.path.insert(0, candidate)

    from docreview360.ml.golden_fixtures import (
        DEFAULT_FIXTURE_DIR,
        generate_golden_fixtures,
    )

    destination = DEFAULT_FIXTURE_DIR
    paths = generate_golden_fixtures(destination)
    for name, path in sorted(paths.items()):
        rel = path.relative_to(Path.cwd()) if path.is_relative_to(Path.cwd()) else path
        print(f"Wrote {name} → {rel}")


if __name__ == "__main__":
    main()
