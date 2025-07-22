"""In-memory project phases management."""

from __future__ import annotations

from typing import List

_phases: List[str] = []


def _bootstrap_sample() -> None:
    """Initialize with a default set of phases."""
    if not _phases:
        _phases.extend(["FAA Review", "Public Comment", "Final Issuance"])


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
