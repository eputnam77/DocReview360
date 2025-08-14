"""Simple AI workload balancer."""

from __future__ import annotations

from typing import Dict

# In-memory registry mapping each worker name to their current active job count.
_workers: Dict[str, int] = {}


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


def assign_job() -> str:
    """Return worker with the fewest active jobs."""
    if not _workers:
        raise RuntimeError("no workers registered")
    worker = min(_workers, key=lambda k: _workers[k])
    _workers[worker] += 1
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


def reset() -> None:
    """Remove all workers and job counts (used in tests)."""
    _workers.clear()
