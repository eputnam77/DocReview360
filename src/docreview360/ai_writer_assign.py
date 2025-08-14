"""AI-assisted technical writer assignment utilities."""

from __future__ import annotations

from typing import Iterable
from threading import Lock

from . import ai_balancer
from .config import CONFIG_FILE, Config
from .search import project_lock, projects, update_project

_balancer_lock = Lock()


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

    # Ensure all candidates are registered with the balancer.
    for cand in cand_list:
        try:
            ai_balancer.register_worker(cand)
        except ValueError:
            # Already registered, which is fine for our purposes.
            pass

    # Gather existing workload and priority adjustments for each candidate.
    counts: dict[str, int] = {w: 0 for w in cand_list}
    priority_adj: dict[str, int] = {w: 0 for w in cand_list}
    with project_lock:
        for proj in projects.values():
            if proj.user in counts:
                counts[proj.user] += 1
                priority_adj[proj.user] += max(proj.priority, 0)

    # Sync balancer counts with existing assignments if needed.
    for cand in cand_list:
        with _balancer_lock:
            if ai_balancer.current_load(cand) < counts[cand]:
                ai_balancer._workers[cand] = counts[cand]  # type: ignore[attr-defined]

    selected = min(
        cand_list,
        key=lambda w: (ai_balancer.current_load(w) + priority_adj[w], w),
    )
    update_project(project_id, user=selected)
    with _balancer_lock:
        ai_balancer._workers[selected] = (  # type: ignore[attr-defined]
            ai_balancer.current_load(selected) + 1
        )
    return selected
