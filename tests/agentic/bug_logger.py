from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .models import BugReport


class BugLoggerAgent:
    """Persists structured bug reports as JSON artifacts."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir

    def record(self, report: BugReport) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        target = self.output_dir / f"{report.id}.json"
        target.write_text(
            json.dumps(_serialize_report(report), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return target


def _serialize_report(report: BugReport) -> dict[str, Any]:
    payload = asdict(report)
    payload["created_at"] = report.created_at.isoformat()
    return payload

