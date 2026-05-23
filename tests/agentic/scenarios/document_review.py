from __future__ import annotations

from ..agents import AdminEdgeCaseAgent, CreatorAgent, FixerAgent, ReviewerAgent
from ..models import Actor, ScenarioState


def run_document_review_scenario(orchestrator, state: ScenarioState) -> None:
    """Run a realistic creator/reviewer/admin document review workflow."""

    creator_actor = Actor(
        username=f"creator-{state.run_id}",
        roles=("admin", "manager", "user"),
        kind="creator",
    )
    reviewer_actor = Actor(
        username=f"reviewer-{state.run_id}",
        roles=("reviewer", "user"),
        kind="reviewer",
    )
    edge_actor = Actor(
        username=f"edge-admin-{state.run_id}",
        roles=("admin", "user"),
        kind="admin_edge",
    )
    inactive_actor = Actor(
        username=f"inactive-{state.run_id}",
        roles=("reviewer", "user"),
        kind="reviewer",
    )

    creator = CreatorAgent(creator_actor, orchestrator.seed_actor(creator_actor, state))
    reviewer = ReviewerAgent(reviewer_actor, orchestrator.seed_actor(reviewer_actor, state))
    admin = AdminEdgeCaseAgent(edge_actor, orchestrator.seed_actor(edge_actor, state))
    fixer = FixerAgent(creator_actor, orchestrator.session_for(creator_actor.username))
    orchestrator.seed_actor(inactive_actor, state)

    creator.ensure_user(reviewer_actor.username, ["reviewer", "user"])
    creator.ensure_user(inactive_actor.username, ["reviewer", "user"])
    project = creator.create_project(state, name="Agentic Harness Review")
    workflow = creator.create_workflow(state, ["draft", "review", "approval"])
    document = creator.upload_document(
        state,
        filename="agentic-review.md",
        content="# Agentic Review\n\nInitial policy draft.",
    )
    creator.assign_reviewer(state, reviewer_actor.username)

    assigned_projects = reviewer.open_assigned_projects()
    if not any(item["id"] == project["id"] for item in assigned_projects):
        raise AssertionError("reviewer could not see assigned project")

    revision_id = reviewer.revise_document(
        state,
        "# Agentic Review\n\nInitial policy draft.\n\nReviewer edit.",
    )
    comment = reviewer.comment(state, "Clarify implementation authority.", tags=["policy"])
    resolved = reviewer.resolve_comment(state, comment["id"])
    approval = creator.create_approval(state, reviewer_actor.username)
    approved = reviewer.approve_with_initials(approval["id"], "RP")

    admin.disable_user(inactive_actor.username)
    admin.assert_disabled_user_cannot_login(inactive_actor.username, inactive_actor.password)
    admin.assert_missing_project_returns_404()

    state.artifacts.update(
        {
            "project": project,
            "workflow": workflow,
            "document": document,
            "revision_id": revision_id,
            "resolved_comment": resolved,
            "approval": approved,
            "fixer_next_action": fixer.summarize_next_action(0),
        }
    )
