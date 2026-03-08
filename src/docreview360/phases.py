"""Project phases management — database-backed.

All phase state is stored in the ``phases`` and ``phase_workflow_links``
database tables.  The previous JSON-file / FileLock persistence layer has been
removed (Tier 2b).
"""

from __future__ import annotations

from typing import Dict, List

from sqlalchemy import delete, select

from .db_store import get_db
from .models import Phase, PhaseWorkflowLink

# Default phases seeded by migration 008.  Exposed here so other modules
# (e.g. tests, e2e_seed) can reference the canonical list without importing
# the migration file directly.
DEFAULT_PHASES: List[str] = [
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


def _bootstrap_if_empty() -> None:
    """Seed default phases when the table is empty (e.g. fresh in-memory DB)."""

    db = get_db()
    with db.session() as conn:
        from sqlalchemy import text as _text

        count = conn.execute(_text("SELECT COUNT(*) FROM phases")).scalar()
        if count:
            return
        for order, name in enumerate(DEFAULT_PHASES, start=1):
            conn.execute(
                _text(
                    "INSERT OR IGNORE INTO phases (name, display_order) VALUES (:name, :order)"
                ),
                {"name": name, "order": order},
            )


def list_phases() -> List[str]:
    """Return all configured phases ordered by display_order."""

    _bootstrap_if_empty()
    db = get_db()
    with db.session() as conn:
        rows = conn.execute(
            select(Phase.name).order_by(Phase.display_order, Phase.name)
        ).all()
        return [row[0] for row in rows]


def list_phase_workflow_links() -> Dict[str, str]:
    """Return a dict mapping phase name → workflow template id."""

    db = get_db()
    with db.session() as conn:
        rows = conn.execute(
            select(Phase.name, PhaseWorkflowLink.workflow_template_id)
            .join(PhaseWorkflowLink, Phase.id == PhaseWorkflowLink.phase_id)
        ).all()
        return {row[0]: row[1] for row in rows}


def get_phase_workflow_template(phase_name: str) -> str | None:
    """Return the linked workflow template id for *phase_name* if set."""

    name = phase_name.strip()
    db = get_db()
    with db.session() as conn:
        row = conn.execute(
            select(PhaseWorkflowLink.workflow_template_id)
            .join(Phase, Phase.id == PhaseWorkflowLink.phase_id)
            .where(Phase.name == name)
        ).one_or_none()
        return row[0] if row else None


def set_phase_workflow_template(phase_name: str, workflow_template_id: str | None) -> None:
    """Set or clear the linked workflow template id for a phase."""

    name = phase_name.strip()
    if not name:
        raise ValueError("phase name cannot be empty")

    from sqlalchemy import text as _text

    db = get_db()
    with db.session() as conn:
        phase_id = conn.execute(
            select(Phase.id).where(Phase.name == name)
        ).scalar_one_or_none()
        if phase_id is None:
            raise KeyError(f"Phase '{name}' not found")

        if workflow_template_id is None or not workflow_template_id.strip():
            conn.execute(
                delete(PhaseWorkflowLink).where(PhaseWorkflowLink.phase_id == phase_id)
            )
        else:
            # Upsert: remove existing link then insert the new one.
            conn.execute(
                delete(PhaseWorkflowLink).where(PhaseWorkflowLink.phase_id == phase_id)
            )
            conn.execute(
                _text(
                    "INSERT INTO phase_workflow_links (phase_id, workflow_template_id) "
                    "VALUES (:pid, :wtid)"
                ),
                {"pid": phase_id, "wtid": workflow_template_id.strip()},
            )


def add_phase(name: str) -> None:
    """Add a new phase if it does not already exist."""

    name = name.strip()
    if not name:
        raise ValueError("phase name cannot be empty")

    from sqlalchemy import text as _text

    db = get_db()
    with db.session() as conn:
        existing = conn.execute(
            select(Phase.id).where(Phase.name == name)
        ).scalar_one_or_none()
        if existing is not None:
            return  # idempotent

        max_order = conn.execute(
            _text("SELECT COALESCE(MAX(display_order), 0) FROM phases")
        ).scalar()
        conn.execute(
            _text(
                "INSERT INTO phases (name, display_order) VALUES (:name, :order)"
            ),
            {"name": name, "order": (max_order or 0) + 1},
        )


def delete_phase(name: str) -> None:
    """Remove a phase by name.

    Normalises the input name to match the behaviour of :func:`add_phase`.
    The associated :class:`PhaseWorkflowLink` row is removed via DB cascade.
    """

    name = name.strip()
    db = get_db()
    with db.session() as conn:
        phase_id = conn.execute(
            select(Phase.id).where(Phase.name == name)
        ).scalar_one_or_none()
        if phase_id is None:
            raise KeyError(f"Phase '{name}' not found")
        conn.execute(delete(Phase).where(Phase.id == phase_id))


def rename_phase(old: str, new: str) -> None:
    """Rename an existing phase from *old* to *new*.

    Raises :class:`KeyError` if *old* does not exist.
    """

    new = new.strip()
    if not new:
        raise ValueError("new phase name cannot be empty")
    old = old.strip()

    from sqlalchemy import text as _text, update

    db = get_db()
    with db.session() as conn:
        phase_id = conn.execute(
            select(Phase.id).where(Phase.name == old)
        ).scalar_one_or_none()
        if phase_id is None:
            raise KeyError(f"Phase '{old}' not found")
        conn.execute(
            update(Phase).where(Phase.id == phase_id).values(name=new)
        )


def reset_phases() -> None:
    """Clear all phases and re-seed defaults.  Intended for test use only."""

    from sqlalchemy import text as _text

    db = get_db()
    with db.session() as conn:
        conn.execute(delete(PhaseWorkflowLink))
        conn.execute(delete(Phase))
        for order, name in enumerate(DEFAULT_PHASES, start=1):
            conn.execute(
                _text(
                    "INSERT INTO phases (name, display_order) VALUES (:name, :order)"
                ),
                {"name": name, "order": order},
            )
