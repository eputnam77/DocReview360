# SPDX-License-Identifier: MIT
"""Lightweight workflow engine for approval step progression."""

from __future__ import annotations

import json
import logging
from typing import List

from .approvals import ApprovalModel, approvals
from .db_store import get_db

_logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Determine active approval steps for workflows."""

    def active_approvals(self, wf_id: str) -> List[ApprovalModel]:
        """Return the currently actionable approval steps for *wf_id*.

        Queries the ``approval_records`` table first so results survive server
        restarts.  Falls back to the in-memory cache when the DB is unavailable
        (e.g. during lightweight unit tests that never initialise a DB).
        """
        steps = self._load_steps_from_db(wf_id)
        if not steps:
            # Fall back to in-memory cache (unit-test / no-DB scenario)
            steps = [a for a in approvals.values() if a.workflow == wf_id]
        if not steps:
            return []

        # Heuristic: in sequential mode, non-current steps are marked "future".
        # In parallel mode all non-approved steps are actionable ("pending").
        is_sequential = any(a.state == "future" for a in steps)
        if not is_sequential:
            return [a for a in steps if a.state != "approved"]

        ordered = sorted(steps, key=lambda a: a.order)
        for step in ordered:
            if step.state != "approved":
                return [step]
        return []

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    def _load_steps_from_db(self, wf_id: str) -> List[ApprovalModel]:
        """Load approval steps for *wf_id* from the database."""
        try:
            from sqlalchemy import text as _text

            db = get_db()
            with db.session() as conn:
                rows = conn.execute(
                    _text(
                        "SELECT data FROM approval_records WHERE workflow_id = :wf_id"
                    ),
                    {"wf_id": wf_id},
                ).fetchall()
            result: List[ApprovalModel] = []
            for (raw,) in rows:
                data = json.loads(raw) if isinstance(raw, str) else raw
                try:
                    approval = ApprovalModel.model_validate(data)
                    # Keep the in-memory cache in sync
                    approvals.setdefault(approval.id, approval)
                    result.append(approval)
                except Exception as exc:  # pragma: no cover - skip corrupt rows
                    _logger.debug("Skipping corrupt approval row: %s", exc)
            return result
        except Exception:  # pragma: no cover - DB not available
            return []


engine = WorkflowEngine()
