from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:  # pragma: no cover - type hints only
    _RunChecks = Callable[[str], dict[str, Any]]
    _run_checks: _RunChecks
else:  # pragma: no cover - optional dependency
    try:
        from GovDocVerify import run_checks as _run_checks
    except Exception:
        from services.document_checker import run_checks as _run_checks  # type: ignore


def run_checks(file_path: str | Path) -> dict[str, Any]:
    """Run document checks using GovDocVerify if available."""
    result = _run_checks(str(file_path))
    if not isinstance(result, dict):
        return {}
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run document checks")
    parser.add_argument("file", help="path to document")
    args = parser.parse_args()

    result = run_checks(args.file)
    print(json.dumps(result))
