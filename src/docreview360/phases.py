"""Project phases management with optional persistence."""

from __future__ import annotations

import json
import os
import warnings
from pathlib import Path
from typing import Dict, List

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
PHASE_WORKFLOW_LINKS_FILE = Path(
    os.getenv("DOCREVIEW360_PHASE_WORKFLOW_LINKS_FILE", "phase_workflow_links.json")
)

_phases: List[str] = []
_phase_workflow_links: Dict[str, str] = {}


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


def _load_phase_workflow_links_from_disk() -> bool:
    """Load phase -> workflow-template links when persistence is enabled."""

    if not DOCREVIEW360_ENABLE_PHASE_PERSISTENCE or not PHASE_WORKFLOW_LINKS_FILE.exists():
        return False

    try:
        with FileLock(f"{PHASE_WORKFLOW_LINKS_FILE}.lock"):
            raw = PHASE_WORKFLOW_LINKS_FILE.read_text()
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            return False

        links: Dict[str, str] = {}
        for key, value in payload.items():
            if not isinstance(key, str) or not isinstance(value, str):
                continue
            phase_name = key.strip()
            workflow_template_id = value.strip()
            if phase_name and workflow_template_id:
                links[phase_name] = workflow_template_id

        _phase_workflow_links.clear()
        _phase_workflow_links.update(links)
        _normalize_phase_workflow_links()
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


def _persist_phase_workflow_links() -> None:
    """Persist phase -> workflow-template links to disk when enabled."""

    if not DOCREVIEW360_ENABLE_PHASE_PERSISTENCE:
        return
    try:
        PHASE_WORKFLOW_LINKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with FileLock(f"{PHASE_WORKFLOW_LINKS_FILE}.lock"):
            PHASE_WORKFLOW_LINKS_FILE.write_text(
                json.dumps(_phase_workflow_links, indent=2)
            )
    except OSError:
        # Best-effort persistence; avoid blocking API operations on IO errors.
        pass


def _normalize_phase_workflow_links() -> None:
    """Drop links that reference phases no longer present."""

    valid_phases = set(_phases)
    stale = [name for name in _phase_workflow_links if name not in valid_phases]
    for name in stale:
        _phase_workflow_links.pop(name, None)


def reset_phases() -> None:
    """Clear phases and remove persisted data if present."""

    _phases.clear()
    _phase_workflow_links.clear()
    if not DOCREVIEW360_ENABLE_PHASE_PERSISTENCE:
        return
    try:
        DATA_FILE.unlink(missing_ok=True)
    except OSError:
        pass
    try:
        PHASE_WORKFLOW_LINKS_FILE.unlink(missing_ok=True)
    except OSError:
        pass


if not _load_phases_from_disk():
    _bootstrap_sample()
_load_phase_workflow_links_from_disk()
_normalize_phase_workflow_links()


def list_phases() -> List[str]:
    """Return all configured phases."""
    return list(_phases)


def list_phase_workflow_links() -> Dict[str, str]:
    """Return a copy of phase -> workflow-template links."""

    _normalize_phase_workflow_links()
    return dict(_phase_workflow_links)


def get_phase_workflow_template(phase_name: str) -> str | None:
    """Return the linked workflow template id for ``phase_name`` if configured."""

    return _phase_workflow_links.get(phase_name.strip())


def set_phase_workflow_template(phase_name: str, workflow_template_id: str | None) -> None:
    """Set or clear the linked workflow template id for a phase."""

    name = phase_name.strip()
    if not name:
        raise ValueError("phase name cannot be empty")
    if name not in _phases:
        raise KeyError(f"Phase '{name}' not found")

    if workflow_template_id is None or not workflow_template_id.strip():
        _phase_workflow_links.pop(name, None)
    else:
        _phase_workflow_links[name] = workflow_template_id.strip()

    _normalize_phase_workflow_links()
    _persist_phase_workflow_links()


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
        _phase_workflow_links.pop(name, None)
        _persist_phases()
        _persist_phase_workflow_links()


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
    if old in _phase_workflow_links:
        _phase_workflow_links[new] = _phase_workflow_links.pop(old)
    _normalize_phase_workflow_links()
    _persist_phases()
    _persist_phase_workflow_links()
