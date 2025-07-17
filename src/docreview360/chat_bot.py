"""Simple AI chat bot helpers."""

from __future__ import annotations

import re
from .search import projects
from .workflows import workflows


async def answer_question(question: str) -> str:
    """Return an answer for ``question`` based on project data."""
    if not question.strip():
        raise ValueError("question must not be empty")

    lower = question.lower()
    who = re.search(r"who is assigned to ([\w-]+)", lower)
    if who:
        proj_id = who.group(1)
        proj = projects.get(proj_id)
        if proj is None:
            return f"Project {proj_id} not found."
        user = proj.temp_user or proj.user
        if user:
            return f"{user} is assigned to {proj_id}."
        return f"No user assigned to {proj_id}."

    status = re.search(r"status of ([\w-]+)", lower)
    if status:
        proj_id = status.group(1)
        wf = next((w for w in workflows.values() if w.project == proj_id), None)
        if wf is None:
            return f"No workflow found for {proj_id}."
        return f"{proj_id} is currently in the {wf.phase} phase."

    return "I don't know."
