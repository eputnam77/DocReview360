"""Simple in-memory worker load balancer used by the AI writer assigner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from prometheus_client import Counter

# In-memory registry mapping each worker name to their current active job count.
_workers: Dict[str, int] = {}

WORKER_REGISTRATIONS = Counter(
    "docreview360_worker_registrations_total", "Number of workers registered"
)
JOB_ASSIGNMENTS = Counter(
    "docreview360_job_assignments_total",
    "Number of jobs assigned to workers",
    ["worker"],
)
WORKER_DEREGISTRATIONS = Counter(
    "docreview360_worker_deregistrations_total", "Number of workers deregistered"
)


def register_worker(name: str) -> None:
    """Register a worker with zero load.

    Raises
    ------
    ValueError
        If ``name`` is empty or already registered.
    """
    if not name:
        raise ValueError("name is required")
    if name in _workers:
        raise ValueError(f"{name} already registered")
    _workers[name] = 0
    WORKER_REGISTRATIONS.inc()


def assign_job() -> str:
    """Return worker with the fewest active jobs."""
    if not _workers:
        raise RuntimeError("no workers registered")
    # ``dict`` preserves insertion order which previously meant the first
    # registered worker was favoured when loads were equal.  Break ties
    # alphabetically so assignments are deterministic regardless of
    # registration order.
    worker = min(_workers, key=lambda k: (_workers[k], k))
    _workers[worker] += 1
    JOB_ASSIGNMENTS.labels(worker=worker).inc()
    return worker


def complete_job(worker: str) -> None:
    """Mark a job as completed for ``worker``."""
    if worker not in _workers:
        raise KeyError(worker)
    _workers[worker] = max(_workers[worker] - 1, 0)


def current_load(worker: str) -> int:
    """Return the number of active jobs for ``worker``."""
    if worker not in _workers:
        raise KeyError(worker)
    return _workers[worker]


def deregister_worker(name: str) -> int:
    """Remove ``name`` from the balancer and return its outstanding load.

    Parameters
    ----------
    name:
        Identifier of the worker to remove.

    Returns
    -------
    int
        The number of active jobs the worker had when removed.

    Raises
    ------
    KeyError
        If ``name`` is not currently registered.
    """
    if name not in _workers:
        raise KeyError(name)
    WORKER_DEREGISTRATIONS.inc()
    return _workers.pop(name)


def reset() -> None:
    """Remove all workers and job counts (used in tests)."""
    _workers.clear()


def save_state(path: str | Path) -> None:
    """Persist the current worker registry to ``path``."""
    with Path(path).open("w", encoding="utf-8") as fh:
        json.dump(_workers, fh)


def load_state(path: str | Path) -> None:
    """Load worker registry from ``path`` if it exists."""
    file = Path(path)
    if not file.exists():
        _workers.clear()
        return
    with file.open("r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid registry format") from exc
    if not isinstance(data, dict):
        raise ValueError("invalid registry format")
    _workers.clear()
    for key, value in data.items():
        try:
            count = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid registry format") from exc
        if count < 0:
            raise ValueError("invalid registry format")
        _workers[str(key)] = count
