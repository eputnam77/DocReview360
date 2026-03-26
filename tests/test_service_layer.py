# SPDX-License-Identifier: MIT
"""Unit tests for the service layer introduced in R-14."""

from __future__ import annotations

import pytest

from docreview360.services import ApprovalService, DocumentService, ProjectService


# ---------------------------------------------------------------------------
# ProjectService
# ---------------------------------------------------------------------------


class TestProjectService:
    def setup_method(self) -> None:
        self.svc = ProjectService()

    def test_get_returns_none_for_missing_project(self) -> None:
        assert self.svc.get("nonexistent-project-id") is None

    def test_list_returns_list(self) -> None:
        result = self.svc.list()
        assert isinstance(result, list)

    def test_list_filtered_by_user_returns_list(self) -> None:
        result = self.svc.list(user="alice")
        assert isinstance(result, list)

    def test_assert_exists_raises_for_missing(self) -> None:
        with pytest.raises(KeyError, match="Project not found"):
            self.svc.assert_exists("no-such-project")

    def test_user_can_view_with_matching_owner(self) -> None:
        from docreview360.search._models import ProjectModel

        project = ProjectModel(
            id="p1",
            name="Test Project",
            user="alice",
            description="",
            status="draft",
        )
        assert self.svc.user_can_view(project, "alice") is True

    def test_user_can_view_with_non_owner(self) -> None:
        from docreview360.search._models import ProjectModel

        project = ProjectModel(
            id="p1",
            name="Test Project",
            user="alice",
            description="",
            status="draft",
        )
        assert self.svc.user_can_view(project, "carol") is False

    def test_user_can_view_with_temp_user(self) -> None:
        from docreview360.search._models import ProjectModel

        project = ProjectModel(
            id="p1",
            name="Test Project",
            user="alice",
            temp_user="bob",
            description="",
            status="draft",
        )
        assert self.svc.user_can_view(project, "bob") is True


# ---------------------------------------------------------------------------
# DocumentService
# ---------------------------------------------------------------------------


class TestDocumentService:
    def setup_method(self) -> None:
        self.svc = DocumentService()

    def test_get_returns_none_for_missing_document(self) -> None:
        assert self.svc.get("nonexistent-doc-id") is None

    def test_list_returns_list(self) -> None:
        result = self.svc.list()
        assert isinstance(result, list)

    def test_list_public_returns_list(self) -> None:
        result = self.svc.list_public()
        assert isinstance(result, list)

    def test_assert_exists_raises_for_missing(self) -> None:
        with pytest.raises(KeyError, match="Document not found"):
            self.svc.assert_exists("no-such-doc")

    def test_is_frozen_returns_false_for_missing(self) -> None:
        # get() returns None; frozen property check should return False
        assert self.svc.is_frozen("no-such-doc") is False


# ---------------------------------------------------------------------------
# ApprovalService
# ---------------------------------------------------------------------------


class TestApprovalService:
    def setup_method(self) -> None:
        self.svc = ApprovalService()

    def test_get_returns_none_for_missing_approval(self) -> None:
        assert self.svc.get("nonexistent-approval-id") is None

    def test_list_returns_list(self) -> None:
        result = self.svc.list()
        assert isinstance(result, list)

    def test_list_filtered_by_workflow(self) -> None:
        result = self.svc.list(workflow="wf-999")
        assert isinstance(result, list)

    def test_assert_exists_raises_for_missing(self) -> None:
        with pytest.raises(KeyError, match="Approval not found"):
            self.svc.assert_exists("no-such-approval")

    def test_is_terminal_approved(self) -> None:
        from docreview360.approvals.core import ApprovalModel

        approval = ApprovalModel(
            id="a1",
            workflow="wf1",
            reviewer="alice",
            document_id="doc1",
            phase_id=None,
            state="approved",
        )
        assert self.svc.is_terminal(approval) is True

    def test_is_terminal_pending(self) -> None:
        from docreview360.approvals.core import ApprovalModel

        approval = ApprovalModel(
            id="a1",
            workflow="wf1",
            reviewer="alice",
            document_id="doc1",
            phase_id=None,
            state="pending",
        )
        assert self.svc.is_terminal(approval) is False

    def test_is_terminal_rejected(self) -> None:
        from docreview360.approvals.core import ApprovalModel

        approval = ApprovalModel(
            id="a1",
            workflow="wf1",
            reviewer="alice",
            document_id="doc1",
            phase_id=None,
            state="rejected",
        )
        assert self.svc.is_terminal(approval) is True
