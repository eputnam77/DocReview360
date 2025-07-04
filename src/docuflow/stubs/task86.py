"""Trivy step validation helper."""

from __future__ import annotations

import yaml

from . import record_task_completion


def has_trivy_step(workflow_yaml: str) -> bool:
    """Return ``True`` if the workflow contains a Trivy step."""
    record_task_completion(86)
    try:
        data = yaml.safe_load(workflow_yaml) or {}
    except yaml.YAMLError:
        return False
    if not isinstance(data, dict):
        return False
    steps = data.get("jobs", {}).get("build", {}).get("steps", [])
    for step in steps:
        name = step.get("name", "")
        uses = step.get("uses", "")
        if "trivy" in name.lower() or "trivy" in str(uses).lower():
            return True
    return False
