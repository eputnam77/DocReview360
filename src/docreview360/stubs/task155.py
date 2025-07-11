"""Terraform plan parser for in-browser viewer (Task 155)."""

from __future__ import annotations

import re
from typing import Dict, List

from . import record_task_completion


def task155(plan: str) -> List[Dict[str, str]]:
    """Parse ``plan`` output and return resource actions."""

    actions: List[Dict[str, str]] = []
    for line in plan.splitlines():
        match = re.match(r"\s*([+~\-])\s*(\S+)", line)
        if not match:
            continue
        op, resource = match.groups()
        actions.append(
            {
                "action": {"+": "create", "~": "update", "-": "destroy"}[op],
                "resource": resource,
            }
        )

    record_task_completion(155)
    return actions
