"""In-memory project phases management."""

from __future__ import annotations

from typing import List

_phases: List[str] = []


def _bootstrap_sample() -> None:
    """Initialize with a default set of phases."""
    if not _phases:
        _phases.extend(["Internal FAA Review", "Public Comment", "Final Issuance"])


_bootstrap_sample()


def list_phases() -> List[str]:
    """Return all configured phases."""
    return list(_phases)


def add_phase(name: str) -> None:
    """Add a new phase if it does not already exist."""
    if name not in _phases:
        _phases.append(name)


def delete_phase(name: str) -> None:
    """Remove a phase by name."""
    try:
        _phases.remove(name)
    except ValueError as exc:
        raise KeyError(f"Phase '{name}' not found") from exc


def rename_phase(old: str, new: str) -> None:
    """Rename an existing phase from ``old`` to ``new``.

    Raises KeyError if ``old`` does not exist.
    """
    try:
        idx = _phases.index(old)
    except ValueError as exc:
        raise KeyError(f"Phase '{old}' not found") from exc
    _phases[idx] = new
