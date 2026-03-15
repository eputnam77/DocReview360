"""Integration tests confirming Tier 1a/1b/1c state persists across server restarts.

A "restart" is simulated by:
1. Clearing the in-memory caches.
2. Calling the load-from-DB helpers that run at real startup.

This proves that any data written through the new DB-persistence layer is
durable and will be recovered after a process restart.
"""

from __future__ import annotations

import json

import pytest

from docreview360.database import Database
from docreview360.db_store import reset_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_db(tmp_path):
    """Give every test its own fresh in-memory SQLite database."""
    db_url = "sqlite+pysqlite:///:memory:"
    reset_db(db_url)
    yield
    # Tear-down: drop the shared DB reference so the next test gets a fresh one
    reset_db(None)


# ---------------------------------------------------------------------------
# Tier 1a — Approvals
# ---------------------------------------------------------------------------


class TestApprovalPersistence:
    """Approvals survive a simulated server restart."""

    def test_approval_created_and_recovered(self):
        """An approval created via create_approval is persisted to DB and
        can be recovered into a fresh in-memory cache."""
        from docreview360.approvals import (
            approvals,
            create_approval,
            get_approval,
            load_approvals_from_db,
            reset_approvals,
        )

        # Create an approval — this also writes to the DB.
        approval = create_approval("wf-restart", "alice", "doc-restart")
        appr_id = approval.id
        assert approvals.get(appr_id) is not None

        # Simulate a server restart: wipe the in-memory dict.
        approvals.clear()
        assert approvals.get(appr_id) is None

        # Restore from DB (this is what _lifespan does at startup).
        load_approvals_from_db()
        recovered = approvals.get(appr_id)
        assert recovered is not None
        assert recovered.id == appr_id
        assert recovered.workflow == "wf-restart"
        assert recovered.reviewer == "alice"

    def test_approval_state_update_persisted(self):
        """Updating approval state is written through to the DB."""
        import asyncio

        from docreview360.approvals import (
            approvals,
            create_approval,
            load_approvals_from_db,
            update_approval_state,
        )

        approval = create_approval("wf-state", "bob", "doc-state")
        appr_id = approval.id

        # Approve it (sequential guard: only first step, order=0)
        asyncio.run(update_approval_state(appr_id, "approved"))
        assert approvals[appr_id].state == "approved"

        # Simulate restart
        approvals.clear()
        load_approvals_from_db()

        recovered = approvals.get(appr_id)
        assert recovered is not None
        assert recovered.state == "approved"

    def test_approval_delete_removes_from_db(self):
        """Deleting an approval removes it from the DB so it isn't recovered."""
        from docreview360.approvals import (
            approvals,
            create_approval,
            delete_approval,
            load_approvals_from_db,
        )
        from docreview360.documents import documents

        # Provide a document so unlink_approval doesn't raise.
        from docreview360.documents import DocumentModel

        doc_id = "doc-delete"
        documents[doc_id] = DocumentModel(id=doc_id, content="x", history=[])

        approval = create_approval("wf-delete", "carol", doc_id)
        appr_id = approval.id

        delete_approval(appr_id)
        approvals.clear()
        load_approvals_from_db()

        assert approvals.get(appr_id) is None

    def test_reset_approvals_clears_db(self):
        """reset_approvals() removes persisted records so they are not recovered."""
        from docreview360.approvals import (
            approvals,
            create_approval,
            load_approvals_from_db,
            reset_approvals,
        )

        create_approval("wf-reset", "dave", "doc-reset")
        reset_approvals()
        # In-memory is empty.
        assert len(approvals) == 0
        # After simulated restart, still empty.
        load_approvals_from_db()
        assert len(approvals) == 0


# ---------------------------------------------------------------------------
# Tier 1b — Workflow instances and templates
# ---------------------------------------------------------------------------


class TestWorkflowPersistence:
    """Workflow instances survive a simulated server restart."""

    def test_workflow_created_and_recovered(self):
        """A workflow created via create_workflow is persisted to DB."""
        from docreview360.workflows import (
            create_workflow,
            load_workflows_from_db,
            workflows,
        )

        wf = create_workflow("proj-restart", ["draft", "review"])
        wf_id = wf.id
        assert workflows.get(wf_id) is not None

        # Simulate restart
        workflows.clear()
        assert workflows.get(wf_id) is None

        load_workflows_from_db()
        recovered = workflows.get(wf_id)
        assert recovered is not None
        assert recovered.project == "proj-restart"
        assert recovered.phases == ["draft", "review"]


class TestWorkflowTemplatePersistence:
    """Workflow template CRUD operations are persisted to DB."""

    def test_create_template_persisted(self, monkeypatch):
        """A newly created workflow template is recoverable from DB."""
        import docreview360.workflows as wf_mod
        from docreview360.workflows import (
            WorkflowTemplatePayload,
            WorkflowTemplateStep,
            _load_templates_from_db,
            create_workflow_template,
            reset_workflow_templates,
            workflow_template_definitions,
        )

        # Disable file persistence to isolate DB-only behaviour.
        monkeypatch.setattr(wf_mod, "DOCREVIEW360_ENABLE_WORKFLOW_TEMPLATE_PERSISTENCE", False)
        reset_workflow_templates(keep_file=True)

        # Re-enable so DB-backed writes are exercised.
        monkeypatch.setattr(wf_mod, "DOCREVIEW360_ENABLE_WORKFLOW_TEMPLATE_PERSISTENCE", True)

        tpl_name = "test-db-template-unique"
        payload = WorkflowTemplatePayload(
            name=tpl_name,
            steps=[WorkflowTemplateStep(role="Reviewer", required=True)],
        )
        create_workflow_template(payload)
        assert tpl_name in workflow_template_definitions

        # Simulate restart: clear definitions, reload from DB only.
        workflow_template_definitions.clear()
        loaded = _load_templates_from_db()
        assert loaded is True
        assert tpl_name in workflow_template_definitions


# ---------------------------------------------------------------------------
# Tier 1c — Webhook subscriptions
# ---------------------------------------------------------------------------


class TestWebhookSubscriptionPersistence:
    """Webhook subscriptions survive a simulated server restart."""

    def test_subscription_persisted_and_recovered(self):
        """A subscription registered via subscribe_webhook is saved to DB."""
        from docreview360.api.webhooks import (
            _add_subscriber_to_db,
            _load_subscribers_from_db,
            _subscribers,
        )

        _subscribers.clear()

        # Add a subscription (as the route handler would do)
        event = "document.published"
        url = "https://example.com/hook"
        row_id = _add_subscriber_to_db(event, url, None)
        _subscribers.setdefault(event, []).append((url, None, row_id))

        # Simulate restart: clear in-memory cache, reload from DB.
        _subscribers.clear()
        assert _subscribers.get(event) is None

        _load_subscribers_from_db()
        assert any(entry[0] == url for entry in _subscribers.get(event, []))

    def test_multiple_subscriptions_recovered(self):
        """Multiple subscriptions for different events are all recovered."""
        from docreview360.api.webhooks import (
            _add_subscriber_to_db,
            _load_subscribers_from_db,
            _subscribers,
        )

        _subscribers.clear()
        entries = [
            ("approval.created", "https://a.example.com/hook"),
            ("approval.created", "https://b.example.com/hook"),
            ("workflow.advanced", "https://c.example.com/hook"),
        ]
        for event, url in entries:
            row_id = _add_subscriber_to_db(event, url, None)
            _subscribers.setdefault(event, []).append((url, None, row_id))

        _subscribers.clear()
        _load_subscribers_from_db()

        assert len(_subscribers.get("approval.created", [])) == 2
        assert len(_subscribers.get("workflow.advanced", [])) == 1


# ---------------------------------------------------------------------------
# Tier 1b — Workflow engine queries DB
# ---------------------------------------------------------------------------


class TestWorkflowEngineDB:
    """WorkflowEngine.active_approvals reads from the DB."""

    def test_active_approvals_from_db(self):
        """active_approvals returns steps loaded from DB (not only in-memory)."""
        from docreview360.approvals import approvals, create_approval
        from docreview360.workflow_engine import engine

        # Create two approvals in sequential mode (order 0 and 1)
        a1 = create_approval("wf-engine", "step1", "doc-engine", order=0, state="pending")
        a2 = create_approval("wf-engine", "step2", "doc-engine", order=1, state="future")

        # Clear in-memory so engine must go to DB
        approvals.clear()

        active = engine.active_approvals("wf-engine")
        assert len(active) == 1
        assert active[0].id == a1.id
