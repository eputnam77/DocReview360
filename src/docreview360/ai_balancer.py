"""Simple AI workload balancer."""

from __future__ import annotations

from typing import Dict
import json
"""Simple in-memory worker load balancer used by the AI writer assigner.

The original implementation relied on :class:`Dict` and :mod:`json` but forgot
to import them, meaning any call to :func:`save_state` or :func:`load_state`
would raise a ``NameError`` at runtime.  These functions are exercised by the
tests added in this kata and are intended to persist the registry to disk.  The
missing imports rendered them unusable and represented a real defect.

We now import the required modules explicitly and document the purpose of the
registry.
"""

from pathlib import Path
from typing import Dict
import json

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
    worker = min(_workers, key=lambda k: _workers[k])
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
        data = json.load(fh)
    _workers.clear()
    for key, value in data.items():
        _workers[str(key)] = int(value)
