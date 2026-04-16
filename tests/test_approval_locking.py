# SPDX-License-Identifier: MIT
"""Tests for approval brittleness fixes: B-01/B-02 locks, B-03 rollback,
B-07 persist rollback, B-08 workflow index, B-13 order uniqueness."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from docreview360.approvals.core import (
    _approval_locks,
    _persist_approval,
    _wa_key,
    _workflow_approvals,
    approvals,
    create_approval,
    delete_approval,
    get_approval_lock,
    get_approvals_for_workflow,
    release_approval_lock,
    reset_approvals,
)
from docreview360.approvals.signatures import (
    SignedApprovalImmutableError,
    update_approval_state,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_approval(
    workflow: str = "wf-test",
    reviewer: str = "alice",
    doc_id: str = "doc-lock-test",
    phase_id: str | None = None,
    order: int = 0,
) -> str:
    """Create an approval and return its ID."""
    approval = create_approval(
        workflow=workflow,
        reviewer=reviewer,
        doc_id=doc_id,
        phase_id=phase_id,
        order=order,
    )
    return approval.id


# ---------------------------------------------------------------------------
# B-01/B-02: Lock identity and per-approval isolation
# ---------------------------------------------------------------------------


class TestGetApprovalLock:
    def test_same_id_returns_same_lock(self) -> None:
        """get_approval_lock returns the identical asyncio.Lock for the same ID."""
        lock_a = get_approval_lock("approval-aaa")
        lock_b = get_approval_lock("approval-aaa")
        assert lock_a is lock_b

    def test_different_ids_return_different_locks(self) -> None:
        """get_approval_lock returns distinct locks for different IDs."""
        lock_x = get_approval_lock("approval-xxx")
        lock_y = get_approval_lock("approval-yyy")
        assert lock_x is not lock_y

    def test_lock_is_asyncio_lock(self) -> None:
        """get_approval_lock always returns an asyncio.Lock instance."""
        lock = get_approval_lock("approval-type-check")
        assert isinstance(lock, asyncio.Lock)

    def test_release_removes_lock(self) -> None:
        """release_approval_lock removes the entry from the registry."""
        get_approval_lock("approval-to-release")
        assert "approval-to-release" in _approval_locks
        release_approval_lock("approval-to-release")
        assert "approval-to-release" not in _approval_locks

    def test_release_nonexistent_is_noop(self) -> None:
        """release_approval_lock on an unknown ID does not raise."""
        release_approval_lock("approval-does-not-exist")  # must not raise


# ---------------------------------------------------------------------------
# B-01/B-02: Concurrent mutation serialization
# ---------------------------------------------------------------------------


class TestConcurrentUpdateSerialization:
    def test_concurrent_approve_same_approval_second_raises(self) -> None:
        """Two concurrent update_approval_state calls for the same approval are
        serialized — the second sees the already-approved state and raises
        SignedApprovalImmutableError.
        """
        approval_id = _make_approval(workflow="wf-concurrent")

        async def _approve(state: str) -> None:
            await update_approval_state(approval_id, state)

        async def _run() -> tuple[list[Exception], list[None]]:
            errors: list[Exception] = []
            successes: list[None] = []

            async def _try_approve(state: str) -> None:
                try:
                    await _approve(state)
                    successes.append(None)
                except (SignedApprovalImmutableError, RuntimeError, Exception) as exc:
                    errors.append(exc)

            # Patch _upload_approval_artifacts to be a fast no-op.
            with patch(
                "docreview360.approvals.signatures._upload_approval_artifacts",
                new=AsyncMock(return_value=None),
            ):
                await asyncio.gather(
                    _try_approve("approved"),
                    _try_approve("approved"),
                )
            return errors, successes

        errors, successes = asyncio.run(_run())
        # Exactly one must succeed, one must fail.
        assert len(successes) == 1
        assert len(errors) == 1
        assert isinstance(errors[0], SignedApprovalImmutableError)


# ---------------------------------------------------------------------------
# B-03: Rollback on artifact upload exhaustion
# ---------------------------------------------------------------------------


class TestArtifactUploadExhaustion:
    def test_raises_runtime_error_on_exhaustion(self) -> None:
        """update_approval_state raises RuntimeError when artifact upload always fails."""
        approval_id = _make_approval(workflow="wf-artifact")

        async def _run() -> None:
            with patch(
                "docreview360.approvals.signatures._upload_approval_artifacts",
                new=AsyncMock(side_effect=OSError("upload failed")),
            ), patch(
                "docreview360.approvals.signatures._upload_retry_policy",
                return_value=__import__(
                    "docreview360.approvals.signatures", fromlist=["_RetryPolicy"]
                )._RetryPolicy(max_attempts=1, base_delay=0.0, max_delay=0.0),
            ):
                await update_approval_state(approval_id, "approved")

        with pytest.raises(RuntimeError, match="Artifact upload failed after exhausting retries"):
            asyncio.run(_run())

    def test_state_rolled_back_on_exhaustion(self) -> None:
        """After upload exhaustion, the approval state is restored to 'pending'."""
        approval_id = _make_approval(workflow="wf-rollback")
        original_state = approvals[approval_id].state

        async def _run() -> None:
            with patch(
                "docreview360.approvals.signatures._upload_approval_artifacts",
                new=AsyncMock(side_effect=OSError("always fails")),
            ), patch(
                "docreview360.approvals.signatures._upload_retry_policy",
                return_value=__import__(
                    "docreview360.approvals.signatures", fromlist=["_RetryPolicy"]
                )._RetryPolicy(max_attempts=1, base_delay=0.0, max_delay=0.0),
            ):
                try:
                    await update_approval_state(approval_id, "approved")
                except RuntimeError:
                    pass

        asyncio.run(_run())
        assert approvals[approval_id].state == original_state
        assert approvals[approval_id].signed_at is None

    def test_signature_id_rolled_back_on_exhaustion(self) -> None:
        """After upload exhaustion, signature_id is restored to its pre-call value."""
        approval_id = _make_approval(workflow="wf-sig-rollback")
        assert approvals[approval_id].signature_id is None

        async def _run() -> None:
            with patch(
                "docreview360.approvals.signatures._upload_approval_artifacts",
                new=AsyncMock(side_effect=OSError("always fails")),
            ), patch(
                "docreview360.approvals.signatures._upload_retry_policy",
                return_value=__import__(
                    "docreview360.approvals.signatures", fromlist=["_RetryPolicy"]
                )._RetryPolicy(max_attempts=1, base_delay=0.0, max_delay=0.0),
            ):
                try:
                    await update_approval_state(
                        approval_id, "approved", signature_id="sig-from-call"
                    )
                except RuntimeError:
                    pass

        asyncio.run(_run())
        # signature_id must revert to None (its pre-call value)
        assert approvals[approval_id].signature_id is None


# ---------------------------------------------------------------------------
# B-07: Persist failure rolls back in-memory state
# ---------------------------------------------------------------------------


class TestPersistFailureRollback:
    def test_rollback_when_previous_provided(self) -> None:
        """_persist_approval restores approvals[id] to previous on DB failure."""
        approval_id = _make_approval(workflow="wf-persist-fail")
        approval = approvals[approval_id]

        # Take a snapshot before mutation.
        old_state = approval.model_copy(deep=True)

        # Mutate state in memory.
        approval.state = "approved"

        # Simulate DB failure.
        with patch(
            "docreview360.approvals.core.get_db",
            side_effect=RuntimeError("DB unavailable"),
        ):
            _persist_approval(approval, previous=old_state)

        # In-memory state should be rolled back to the pre-mutation snapshot.
        assert approvals[approval_id].state == "pending"

    def test_no_rollback_when_previous_is_none(self) -> None:
        """_persist_approval does NOT restore approvals[id] when previous=None."""
        approval_id = _make_approval(workflow="wf-persist-no-rollback")
        approval = approvals[approval_id]

        # Mutate state in memory.
        approval.state = "approved"

        with patch(
            "docreview360.approvals.core.get_db",
            side_effect=RuntimeError("DB unavailable"),
        ):
            _persist_approval(approval, previous=None)

        # Without previous, in-memory state is left as mutated.
        assert approvals[approval_id].state == "approved"


# ---------------------------------------------------------------------------
# B-08: Workflow approval index
# ---------------------------------------------------------------------------


class TestGetApprovalsForWorkflow:
    def test_returns_correct_approvals_for_workflow(self) -> None:
        """get_approvals_for_workflow returns exactly the approvals in that workflow."""
        wf = "wf-index-test"
        aid1 = _make_approval(workflow=wf, reviewer="alice", doc_id="d1")
        aid2 = _make_approval(workflow=wf, reviewer="bob", doc_id="d2")
        _make_approval(workflow="wf-other", reviewer="carol", doc_id="d3")

        result = get_approvals_for_workflow(wf)
        ids = {a.id for a in result}
        assert aid1 in ids
        assert aid2 in ids
        assert len(result) == 2

    def test_filters_by_phase_id(self) -> None:
        """get_approvals_for_workflow with phase_id only returns matching phase."""
        wf = "wf-phase-filter"
        aid_p1 = _make_approval(workflow=wf, phase_id="phase-1", doc_id="dp1")
        aid_p2 = _make_approval(workflow=wf, phase_id="phase-2", doc_id="dp2")

        result_p1 = get_approvals_for_workflow(wf, "phase-1")
        assert len(result_p1) == 1
        assert result_p1[0].id == aid_p1

        result_p2 = get_approvals_for_workflow(wf, "phase-2")
        assert len(result_p2) == 1
        assert result_p2[0].id == aid_p2

    def test_empty_for_unknown_workflow(self) -> None:
        """get_approvals_for_workflow returns [] for a workflow with no approvals."""
        result = get_approvals_for_workflow("wf-does-not-exist")
        assert result == []

    def test_delete_removes_from_index(self) -> None:
        """Deleting an approval removes it from the workflow index."""
        wf = "wf-delete-index"
        aid = _make_approval(workflow=wf, doc_id="d-del")
        assert len(get_approvals_for_workflow(wf)) == 1

        delete_approval(aid)
        assert get_approvals_for_workflow(wf) == []

    def test_index_key_uses_phase_id(self) -> None:
        """Secondary index key includes phase_id for scoped lookups."""
        assert _wa_key("wf", "p1") == "wf:p1"
        assert _wa_key("wf", None) == "wf:"

    def test_reset_approvals_clears_index(self) -> None:
        """reset_approvals() clears the workflow index."""
        _make_approval(workflow="wf-reset-test", doc_id="d-r")
        assert _workflow_approvals  # non-empty before reset
        reset_approvals()
        assert _workflow_approvals == {}


# ---------------------------------------------------------------------------
# B-13: Order uniqueness within workflow/phase
# ---------------------------------------------------------------------------


class TestOrderUniqueness:
    def test_duplicate_order_same_workflow_raises(self) -> None:
        """Creating two approvals with the same order in the same workflow raises ValueError."""
        wf = "wf-order-unique"
        create_approval(workflow=wf, reviewer="alice", doc_id="d-ord1", order=1)
        with pytest.raises(ValueError, match="order=1"):
            create_approval(workflow=wf, reviewer="bob", doc_id="d-ord2", order=1)

    def test_duplicate_order_same_workflow_and_phase_raises(self) -> None:
        """Same order in the same workflow+phase raises ValueError."""
        wf = "wf-order-phase-dup"
        create_approval(
            workflow=wf, reviewer="alice", doc_id="d-ord-p1", phase_id="phase-a", order=2
        )
        with pytest.raises(ValueError, match="order=2"):
            create_approval(
                workflow=wf, reviewer="bob", doc_id="d-ord-p2", phase_id="phase-a", order=2
            )

    def test_same_order_different_phases_ok(self) -> None:
        """Same order in different phases of the same workflow is allowed."""
        wf = "wf-order-diff-phases"
        a1 = create_approval(
            workflow=wf, reviewer="alice", doc_id="d-diff-p1", phase_id="phase-1", order=1
        )
        a2 = create_approval(
            workflow=wf, reviewer="bob", doc_id="d-diff-p2", phase_id="phase-2", order=1
        )
        assert a1.order == a2.order == 1
        assert a1.phase_id != a2.phase_id

    def test_order_zero_bypasses_uniqueness_check(self) -> None:
        """order=0 (the default) skips the uniqueness check and allows duplicates."""
        wf = "wf-order-zero"
        create_approval(workflow=wf, reviewer="alice", doc_id="d-zero1", order=0)
        # Should not raise.
        create_approval(workflow=wf, reviewer="bob", doc_id="d-zero2", order=0)

    def test_same_order_different_workflows_ok(self) -> None:
        """Same order value in completely different workflows is allowed."""
        create_approval(workflow="wf-a", reviewer="alice", doc_id="d-wa", order=5)
        a2 = create_approval(workflow="wf-b", reviewer="bob", doc_id="d-wb", order=5)
        assert a2.order == 5
