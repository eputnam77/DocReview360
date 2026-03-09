"""AI-assisted technical writer assignment utilities."""

from __future__ import annotations

import logging
from contextlib import suppress
from threading import Lock
from typing import Iterable

from . import ai_balancer, auth
from .config import CONFIG_FILE, Config
from .search import project_lock, projects, update_project

_balancer_lock = Lock()
_logger = logging.getLogger(__name__)


def assign_technical_writer(  # noqa: C901
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

    # ``auth.is_active`` returns ``False`` for explicitly disabled users but also
    # for usernames that do not yet exist in the credential store.  The AI
    # balancer receives candidate lists sourced from other services (for
    # example, HR sync) where new writers may appear before their accounts are
    # provisioned.  Filtering those names out meant we never registered them
    # with the balancer which in turn caused ``KeyError`` when their load was
    # inspected.  Treat missing users as available so that new writers can be
    # considered immediately while still honouring the "inactive" flag when it
    # is present.
    cand_list: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        record = auth.USER_REPOSITORY.get_user(candidate)
        if record is None:
            cand_list.append(candidate)
            continue
        if auth.is_active(candidate):
            cand_list.append(candidate)
    if not cand_list:
        raise ValueError("candidates is required")

    project = projects.get(project_id)
    if project is None:
        raise ValueError(f"unknown project {project_id}")

    # Ensure all candidates are registered with the balancer.
    for cand in cand_list:
        with suppress(ValueError):
            # Already registered, which is fine for our purposes.
            ai_balancer.register_worker(cand)

    # Gather existing workload and priority adjustments for each candidate.
    counts: dict[str, int] = {w: 0 for w in cand_list}
    priority_adj: dict[str, int] = {w: 0 for w in cand_list}
    with project_lock:
        for pid, proj in projects.items():
            if pid != "demo-project" and proj.user in counts:
                counts[proj.user] += 1
                priority_adj[proj.user] += max(proj.priority, 0)

    # Sync balancer counts with existing assignments if needed.
    for cand in cand_list:
        with _balancer_lock:
            if ai_balancer.current_load(cand) < counts[cand]:
                ai_balancer._workers[cand] = counts[cand]

    with _balancer_lock:

        def _load_key(worker: str) -> tuple[int, str]:
            return (ai_balancer._workers.get(worker, 0) + priority_adj[worker], worker)

        selected = min(cand_list, key=_load_key)
        ai_balancer._workers[selected] = ai_balancer._workers.get(selected, 0) + 1
    update_project(project_id, user=selected)
    return selected


def reassign_projects_from_writer(
    writer: str, candidates: Iterable[str], cfg: Config | None = None
) -> list[str]:
    """Reassign all projects currently handled by ``writer``.

    Parameters
    ----------
    writer:
        The departing writer whose projects should be reassigned.
    candidates:
        Iterable of alternative writer usernames. ``writer`` is ignored if
        present in this iterable.
    cfg:
        Optional configuration. When omitted, the global config file is used.

    Returns
    -------
    list[str]
        IDs of the projects that were reassigned.

    Raises
    ------
    RuntimeError
        If AI auto-assignment is disabled.
    ValueError
        If no candidate writers are provided.
    """
    cfg = cfg or Config.load(CONFIG_FILE)
    if not cfg or not cfg.ai_auto_assign_writers:
        raise RuntimeError("AI auto-assignment disabled")

    cand_list = []
    seen = {writer}
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        record = auth.USER_REPOSITORY.get_user(candidate)
        if record is None:
            cand_list.append(candidate)
            continue
        if auth.is_active(candidate):
            cand_list.append(candidate)
    if not cand_list:
        raise ValueError("candidates is required")

    with project_lock:
        to_reassign = [pid for pid, proj in projects.items() if proj.user == writer]

    for pid in to_reassign:
        # Decrement load for departing writer if tracked.
        try:
            ai_balancer.complete_job(writer)
        except KeyError as exc:
            _logger.warning("complete_job failed for writer %r: %s", writer, exc)
        assign_technical_writer(pid, cand_list, cfg)

    try:
        ai_balancer.deregister_worker(writer)
    except KeyError as exc:
        _logger.warning("deregister_worker failed for writer %r: %s", writer, exc)

    return to_reassign
