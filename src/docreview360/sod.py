# SPDX-License-Identifier: MIT
"""Separation of Duties (SoD) enforcement for approval workflows."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Callable

_TRUE_VALUES = {"1", "true", "yes", "on"}


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class SoDViolationError(Exception):
    """Raised when a Separation of Duties rule is violated."""

    def __init__(self, rule_name: str, message: str) -> None:
        super().__init__(message)
        self.rule_name = rule_name
        self.message = message

    def __str__(self) -> str:
        return f"SoD violation [{self.rule_name}]: {self.message}"


# ---------------------------------------------------------------------------
# Rule dataclass
# ---------------------------------------------------------------------------


@dataclass
class SodRule:
    """A single Separation of Duties rule."""

    name: str
    description: str
    enabled: bool = True
    check: Callable[[str, str | None, str | None], None] = field(repr=False, default=lambda *a: None)


# ---------------------------------------------------------------------------
# Global rule registry
# ---------------------------------------------------------------------------

_SOD_RULES: list[SodRule] = []


def register_sod_rule(
    name: str,
    description: str,
    check_fn: Callable[[str, str | None, str | None], None],
    *,
    enabled: bool = True,
) -> None:
    """Register or replace a SoD rule by name."""
    for i, rule in enumerate(_SOD_RULES):
        if rule.name == name:
            _SOD_RULES[i] = SodRule(name=name, description=description, enabled=enabled, check=check_fn)
            return
    _SOD_RULES.append(SodRule(name=name, description=description, enabled=enabled, check=check_fn))


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def sod_enabled() -> bool:
    """Return True when SoD enforcement is enabled."""
    return os.getenv("DOCREVIEW360_SOD_ENABLED", "true").strip().lower() in _TRUE_VALUES


# ---------------------------------------------------------------------------
# Main enforcement
# ---------------------------------------------------------------------------


def check_approval_sod(
    user_id: str,
    document_id: str | None,
    workflow_id: str | None,
) -> None:
    """Check all enabled SoD rules and raise on any violation.

    Collects all violations and raises a combined :class:`SoDViolationError`
    naming the first violated rule.
    """
    if not sod_enabled():
        return
    violations: list[SoDViolationError] = []
    for rule in _SOD_RULES:
        if not rule.enabled:
            continue
        try:
            rule.check(user_id, document_id, workflow_id)
        except SoDViolationError as exc:
            violations.append(exc)
    if violations:
        # Raise the first violation; include count if multiple
        first = violations[0]
        if len(violations) > 1:
            msg = f"{first.message} (and {len(violations) - 1} more violation(s))"
            raise SoDViolationError(first.rule_name, msg)
        raise first


# ---------------------------------------------------------------------------
# Default rule implementations
# ---------------------------------------------------------------------------


def _check_no_self_approval(
    user_id: str, document_id: str | None, workflow_id: str | None
) -> None:
    """A user cannot approve a document they uploaded/submitted."""
    if not document_id:
        return
    try:
        from .documents import documents
        doc = documents.get(document_id)
    except Exception:
        return
    if doc is None:
        return
    # Check both common field names defensively
    uploader = getattr(doc, "uploader", None) or getattr(doc, "user", None)
    if uploader and uploader == user_id:
        raise SoDViolationError(
            "no_self_approval",
            f"User {user_id!r} cannot approve a document they uploaded (document {document_id!r})",
        )


def _check_no_workflow_creator_approval(
    user_id: str, document_id: str | None, workflow_id: str | None
) -> None:
    """A workflow's creator cannot be its sole approver."""
    if not workflow_id:
        return
    try:
        from .workflows import workflows
        from .approvals import approvals
        wf = workflows.get(workflow_id)
    except Exception:
        return
    if wf is None:
        return
    created_by = getattr(wf, "created_by", None)
    if not created_by or created_by != user_id:
        return
    # Check if any other user has already approved this workflow
    try:
        other_approvers_approved = any(
            a.reviewer != user_id and a.state == "approved" and a.workflow == workflow_id
            for a in approvals.values()
        )
    except Exception:
        return
    if not other_approvers_approved:
        raise SoDViolationError(
            "no_workflow_creator_approval",
            f"User {user_id!r} created workflow {workflow_id!r} and cannot be the sole approver",
        )


def _check_role_conflict(
    user_id: str, document_id: str | None, workflow_id: str | None
) -> None:
    """Enforce configurable role conflict rules from DOCREVIEW360_SOD_ROLE_CONFLICTS."""
    raw = os.getenv("DOCREVIEW360_SOD_ROLE_CONFLICTS", "").strip()
    if not raw:
        return
    try:
        conflicts: dict[str, list[str]] = json.loads(raw)
    except Exception:
        return
    if not conflicts:
        return
    try:
        from .rbac import get_roles
        user_roles = get_roles(user_id)
    except Exception:
        return
    for role, conflicting_roles in conflicts.items():
        if role in user_roles:
            for conflict_role in conflicting_roles:
                if conflict_role in user_roles:
                    raise SoDViolationError(
                        "role_conflict",
                        f"User {user_id!r} has both role {role!r} and conflicting role "
                        f"{conflict_role!r} for this operation",
                    )


# ---------------------------------------------------------------------------
# Management helpers
# ---------------------------------------------------------------------------


def list_sod_rules() -> list[dict]:
    """Return all registered SoD rules as dicts."""
    return [
        {"name": r.name, "description": r.description, "enabled": r.enabled}
        for r in _SOD_RULES
    ]


def set_sod_rule_enabled(name: str, enabled: bool) -> bool:
    """Enable or disable a rule by name. Returns True if found."""
    for rule in _SOD_RULES:
        if rule.name == name:
            rule.enabled = enabled
            return True
    return False


# ---------------------------------------------------------------------------
# Register default rules at module load
# ---------------------------------------------------------------------------


def _register_default_rules() -> None:
    register_sod_rule(
        "no_self_approval",
        "A user cannot approve a document they uploaded or submitted",
        _check_no_self_approval,
    )
    register_sod_rule(
        "no_workflow_creator_approval",
        "A workflow's creator cannot be its sole approver",
        _check_no_workflow_creator_approval,
    )
    register_sod_rule(
        "role_conflict",
        "Enforce configurable role-conflict rules via DOCREVIEW360_SOD_ROLE_CONFLICTS (JSON)",
        _check_role_conflict,
    )


_register_default_rules()
