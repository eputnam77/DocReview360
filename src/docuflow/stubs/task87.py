"""Helm chart rendering stub."""

from __future__ import annotations

from typing import Any

from . import record_task_completion


def render_chart(name: str, values: dict[str, Any]) -> str:
    """Return a simple YAML string rendered from ``values``."""
    if not isinstance(name, str):
        raise TypeError("chart name must be a string")
    record_task_completion(87)
    lines = [f"{name}:"]
    for key, val in values.items():
        lines.append(f"  {key}: {val}")
    return "\n".join(lines)
