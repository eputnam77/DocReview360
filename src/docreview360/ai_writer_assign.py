"""AI-assisted technical writer assignment utilities."""

from __future__ import annotations

from typing import Iterable

from .config import CONFIG_FILE, Config
from .search import projects, update_project


def assign_technical_writer(
    project_id: str,
    candidates: Iterable[str],
    cfg: Config | None = None,
) -> str:
    """Assign the best technical writer to ``project_id``.

    Writers with fewer active assignments and lower accumulated priority are
    preferred. The project is updated with the selected writer.

    Parameters
    ----------
    project_id:
        Identifier of the project to assign.
    candidates:
        Iterable of available technical writer usernames.
    cfg:
        Optional configuration. When omitted, the global config file is loaded.

    Returns
    -------
    str
        The username of the assigned writer.

    Raises
    ------
    RuntimeError
        If AI auto-assignment is disabled in the configuration.
    ValueError
        If ``candidates`` is empty or the project does not exist.
    """
    cfg = cfg or Config.load(CONFIG_FILE)
    if not cfg or not cfg.ai_auto_assign_writers:
        raise RuntimeError("AI auto-assignment disabled")

    cand_list = list(candidates)
    if not cand_list:
        raise ValueError("candidates is required")

    project = projects.get(project_id)
    if project is None:
        raise ValueError(f"unknown project {project_id}")

    workload: dict[str, int] = {w: 0 for w in cand_list}
    for proj in projects.values():
        if proj.user in workload:
            workload[proj.user] += 1 + max(proj.priority, 0)

    selected = min(cand_list, key=lambda w: (workload[w], w))
    update_project(project_id, user=selected)
    return selected
