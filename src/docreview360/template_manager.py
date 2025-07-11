"""Manage golden Markdown templates (Task 143)."""

from __future__ import annotations

from pathlib import Path
from typing import List

from .stubs import record_task_completion

TEMPLATES_DIR = Path("templates/golden")


def save_template(name: str, content: str, root: Path = TEMPLATES_DIR) -> Path:
    """Save ``content`` under ``name`` in ``root`` and return the path."""
    if not name:
        raise ValueError("name is required")
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{name}.md"
    path.write_text(content)
    record_task_completion(143)
    return path


def list_templates(root: Path = TEMPLATES_DIR) -> List[str]:
    """Return available template names."""
    if not root.exists():
        return []
    return [p.stem for p in root.glob("*.md")]
