"""In-memory project phases management."""

from __future__ import annotations

from typing import List

_phases: List[str] = []


def _bootstrap_sample() -> None:
    """Initialize with a default set of phases."""
    if not _phases:
        _phases.extend(
            [
                "Beta Documentation Review",
                "Draft Development",
                "Final Issuance",
                "General Availability",
                "Internal Coordination",
                "Maintenance / Revision Cycle",
                "Peer Review",
                "Public Comment / Proposed Rulemaking",
                "Release Candidate Review",
            ]
        )


_bootstrap_sample()


def list_phases() -> List[str]:
    """Return all configured phases."""
    return list(_phases)


def add_phase(name: str) -> None:
    """Add a new phase if it does not already exist."""
    name = name.strip()
    if not name:
        raise ValueError("phase name cannot be empty")
    if name not in _phases:
        _phases.append(name)


def delete_phase(name: str) -> None:
    """Remove a phase by name.

    ``add_phase`` trims surrounding whitespace when inserting new phases, but
    ``delete_phase`` previously compared the provided name verbatim.  Passing a
    name with incidental spaces would therefore fail to match an existing
    entry.  Normalizing the input keeps the behaviour consistent across the
    API.
    """
    name = name.strip()
    try:
        _phases.remove(name)
    except ValueError as exc:
        raise KeyError(f"Phase '{name}' not found") from exc


def rename_phase(old: str, new: str) -> None:
    """Rename an existing phase from ``old`` to ``new``.

    Raises KeyError if ``old`` does not exist.
    """
    new = new.strip()
    if not new:
        raise ValueError("new phase name cannot be empty")
    old = old.strip()
    try:
        idx = _phases.index(old)
    except ValueError as exc:
        raise KeyError(f"Phase '{old}' not found") from exc
    _phases[idx] = new
