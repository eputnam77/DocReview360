"""Release notes generation helpers for release packaging workflows."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Sequence
import tomllib


def read_project_version(pyproject_path: Path) -> str:
    """Return ``[project].version`` from ``pyproject.toml`` or ``unknown``."""

    if not pyproject_path.exists():
        return "unknown"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict):
        return "unknown"
    version = project.get("version")
    if isinstance(version, str) and version.strip():
        return version.strip()
    return "unknown"


def _normalize_digests(container_digests: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    for digest_ref in container_digests:
        cleaned = digest_ref.strip()
        if not cleaned:
            continue
        if "@sha256:" not in cleaned:
            raise ValueError(
                "invalid digest reference: expected '<image>@sha256:<digest>' format"
            )
        normalized.append(cleaned)
    return normalized


def generate_release_notes(
    output_path: Path,
    *,
    version: str,
    container_digests: Sequence[str] | None = None,
    release_date: date | None = None,
) -> Path:
    """Write release notes to ``output_path`` and return the resulting path."""

    effective_date = release_date or date.today()
    digests = _normalize_digests(container_digests or [])

    lines = [
        f"# DocReview360 v{version} Release Notes",
        "",
        f"Release date: {effective_date.isoformat()}",
        "",
        "## Container Images",
    ]

    if digests:
        lines.append("The following immutable container digests were published for this release:")
        lines.append("")
        for digest_ref in digests:
            lines.append(f"- `{digest_ref}`")
    else:
        lines.append("No container digests were provided for this release.")

    lines.extend(["", "## Verification", "- Verify each digest before deployment."])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path
