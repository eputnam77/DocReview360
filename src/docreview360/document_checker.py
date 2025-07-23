from __future__ import annotations

# mypy: ignore-errors
import json
from pathlib import Path
from typing import Any, cast

try:
    from GovDocVerify import run_checks as _run_checks
except Exception:  # pragma: no cover - optional dep
    from services.document_checker import run_checks as _run_checks


def run_checks(file_path: str | Path) -> dict[str, Any]:
    """Run document checks using GovDocVerify if available."""
    return cast(dict[str, Any], _run_checks(str(file_path)))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run document checks")
    parser.add_argument("file", help="path to document")
    args = parser.parse_args()

    result = run_checks(args.file)
    print(json.dumps(result))
