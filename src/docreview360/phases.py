"""Project phases management with optional persistence."""

from __future__ import annotations

import json
import os
import warnings
from pathlib import Path
from typing import List

from filelock import FileLock


def _env_flag_enabled(value: str | None) -> bool:
    """Interpret truthy string values for the persistence feature flag."""

    if value is None:
        return True
    normalized = value.strip().lower()
    return normalized not in {"0", "false", "no", "off"}


DOCREVIEW360_ENABLE_PHASE_PERSISTENCE = _env_flag_enabled(
    os.getenv("DOCREVIEW360_ENABLE_PHASE_PERSISTENCE")
)

if not DOCREVIEW360_ENABLE_PHASE_PERSISTENCE:
    warnings.warn(
        "Phase persistence is disabled; customizations will not be saved.",
        RuntimeWarning,
        stacklevel=2,
    )

# Path to store persistent phase data
DATA_FILE = Path(os.getenv("DOCREVIEW360_PHASES_FILE", "phases.json"))

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


def _load_phases_from_disk() -> bool:
    """Load phases from disk if persistence is enabled and data exists."""

    if not DOCREVIEW360_ENABLE_PHASE_PERSISTENCE or not DATA_FILE.exists():
        return False
    try:
        with FileLock(f"{DATA_FILE}.lock"):
            raw = DATA_FILE.read_text()
        payload = json.loads(raw)
        if not isinstance(payload, list):
            return False
        phases = [
            item.strip() for item in payload if isinstance(item, str) and item.strip()
        ]
        _phases.clear()
        _phases.extend(phases)
        return True
    except (OSError, json.JSONDecodeError):
        return False


def _persist_phases() -> None:
    """Persist phases to disk if persistence is enabled."""

    if not DOCREVIEW360_ENABLE_PHASE_PERSISTENCE:
        return
    try:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        with FileLock(f"{DATA_FILE}.lock"):
            DATA_FILE.write_text(json.dumps(_phases, indent=2))
    except OSError:
        # Best-effort persistence; avoid blocking API operations on IO errors.
        pass


def reset_phases() -> None:
    """Clear phases and remove persisted data if present."""

    _phases.clear()
    if not DOCREVIEW360_ENABLE_PHASE_PERSISTENCE:
        return
    try:
        DATA_FILE.unlink(missing_ok=True)
    except OSError:
        pass


if not _load_phases_from_disk():
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
        _persist_phases()


def delete_phase(name: str) -> None:
    """Remove a phase by name.

    ``add_phase`` trims surrounding whitespace when inserting new phases, but
    ``delete_phase`` previously compared the provided name verbatim.  Passing a
    name with incidental spaces would therefore fail to match an existing
    entry.  Normalizing the input keeps the behavior consistent across the
    API.
    """
    name = name.strip()
    try:
        _phases.remove(name)
    except ValueError as exc:
        raise KeyError(f"Phase '{name}' not found") from exc
    else:
        _persist_phases()


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
    _persist_phases()
