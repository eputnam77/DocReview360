from __future__ import annotations

from abc import ABC
from typing import Any

from ..api_client import ActorSession
from ..models import Actor, ScenarioState


class Agent(ABC):
    """Base class for persona agents."""

    def __init__(self, actor: Actor, session: ActorSession) -> None:
        self.actor = actor
        self.session = session


class CreatorAgent(Agent):
    """Creates projects, documents, reviewers, and approvals."""

    def ensure_user(self, username: str, roles: list[str]) -> None:
        response = self.session.request(
            "POST",
            "/users",
            json={"username": username, "roles": roles, "active": True},
            expected=(201, 409),
        )
        if response.status_code == 409:
            self.session.request(
                "PUT",
                f"/users/{username}",
                json={"roles": roles, "active": True},
            )

    def create_project(self, state: ScenarioState, *, name: str) -> dict[str, Any]:
        project_id = f"agentic-{state.run_id}"
        response = self.session.request(
            "POST",
            "/projects",
            json={
                "id": project_id,
                "name": name,
                "user": self.actor.username,
            },
            expected=(201, 409),
        )
        if response.status_code == 409:
            response = self.session.request("GET", f"/projects/{project_id}")
        project = response.json()
        state.project_id = project["id"]
        return project

    def create_workflow(self, state: ScenarioState, phases: list[str]) -> dict[str, Any]:
        if state.project_id is None:
            raise ValueError("project_id is required before creating a workflow")
        # Ensure all phases exist in the DB before creating the workflow
        for phase in phases:
            self.session.request("POST", "/phases", json={"name": phase}, expected=(201, 409))
        response = self.session.request(
            "POST",
            "/workflows",
            json={"project": state.project_id, "phases": phases},
            expected=201,
        )
        workflow = response.json()
        state.workflow_id = workflow["id"]
        return workflow

    def upload_document(
        self,
        state: ScenarioState,
        *,
        filename: str,
        content: str,
    ) -> dict[str, Any]:
        if state.project_id is None:
            raise ValueError("project_id is required before uploading a document")
        response = self.session.request(
            "POST",
            "/documents/import",
            data={"project": state.project_id, "user": self.actor.username},
            files={"file": (filename, content, "text/markdown")},
            expected=201,
        )
        document = response.json()
        state.document_id = document["id"]
        return document

    def assign_reviewer(self, state: ScenarioState, reviewer: str) -> list[str]:
        if state.project_id is None:
            raise ValueError("project_id is required before assigning reviewers")
        response = self.session.request(
            "POST",
            f"/projects/{state.project_id}/reviewers",
            json={"reviewer": reviewer},
        )
        return response.json()

    def create_approval(self, state: ScenarioState, reviewer: str) -> dict[str, Any]:
        if state.workflow_id is None:
            raise ValueError("workflow_id is required before creating approvals")
        if state.document_id is None:
            raise ValueError("document_id is required before creating approvals")
        response = self.session.request(
            "POST",
            "/approvals",
            json={
                "workflow": state.workflow_id,
                "reviewer": reviewer,
                "doc_id": state.document_id,
                "description": "Agentic review approval",
            },
            expected=201,
        )
        approval = response.json()
        state.approval_ids.append(approval["id"])
        return approval


class ReviewerAgent(Agent):
    """Acts on assigned review work."""

    def open_assigned_projects(self) -> list[dict[str, Any]]:
        response = self.session.request("GET", f"/projects/assigned/{self.actor.username}")
        return response.json()

    def revise_document(self, state: ScenarioState, content: str) -> str:
        if state.document_id is None:
            raise ValueError("document_id is required before revising a document")
        response = self.session.request(
            "POST",
            f"/documents/{state.document_id}/revisions",
            json={"content": content},
            expected=201,
        )
        return response.json()["revisionId"]

    def comment(
        self,
        state: ScenarioState,
        text: str,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        if state.document_id is None:
            raise ValueError("document_id is required before commenting")
        response = self.session.request(
            "POST",
            f"/documents/{state.document_id}/comments",
            json={"user": self.actor.username, "text": text, "tags": tags or []},
            expected=201,
        )
        comment = response.json()
        state.comment_ids.append(comment["id"])
        return comment

    def resolve_comment(self, state: ScenarioState, comment_id: str) -> dict[str, Any]:
        if state.document_id is None:
            raise ValueError("document_id is required before resolving a comment")
        response = self.session.request(
            "PUT",
            f"/documents/{state.document_id}/comments/{comment_id}",
            json={"status": "resolved"},
        )
        return response.json()

    def approve_with_initials(self, approval_id: str, initials: str) -> dict[str, Any]:
        response = self.session.request(
            "POST",
            f"/approvals/{approval_id}/sign-initials",
            json={"initials": initials},
        )
        return response.json()

    def reject(self, approval_id: str) -> dict[str, Any]:
        response = self.session.request(
            "PUT",
            f"/approvals/{approval_id}",
            json={"state": "rejected"},
        )
        return response.json()


class AdminEdgeCaseAgent(Agent):
    """Exercises permission and invalid-state edges."""

    def disable_user(self, username: str) -> dict[str, Any]:
        response = self.session.request(
            "POST",
            f"/admin/users/{username}/status",
            json={"active": False},
        )
        return response.json()

    def assert_disabled_user_cannot_login(self, username: str, password: str) -> None:
        self.session.request(
            "POST",
            "/token",
            json={"username": username, "password": password},
            headers={"Authorization": ""},
            expected=(400, 401, 403),
        )

    def assert_missing_project_returns_404(self) -> None:
        self.session.request("GET", "/projects/missing-agentic-project", expected=404)


class FixerAgent(Agent):
    """Placeholder hook for regression-loop integrations.

    The local harness records enough structured evidence for Codex or CI to
    pick up failures and add code fixes plus regression tests in the same repo.
    """

    def summarize_next_action(self, bug_count: int) -> str:
        if bug_count == 0:
            return "No code fix required."
        return (
            f"Investigate {bug_count} bug report(s), patch app code, "
            "add regression tests, rerun scenario."
        )
