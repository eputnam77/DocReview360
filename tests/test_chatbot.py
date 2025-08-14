from datetime import datetime, timedelta, timezone

import pytest

from docreview360 import chat_bot
from docreview360.approvals import create_approval, update_approval_state
from docreview360.doc_types import DocumentTypeModel, add_document_type
from docreview360.search import ProjectModel, add_project
from docreview360.workflows import create_workflow


@pytest.mark.asyncio
async def test_assigned_user() -> None:
    add_project(ProjectModel(id="p1", name="Demo", user="alice"))
    resp = await chat_bot.answer_question("Who is assigned to p1?")
    assert resp == "alice is assigned to p1."


@pytest.mark.asyncio
async def test_project_status() -> None:
    add_project(ProjectModel(id="p2", name="Demo2"))
    create_workflow("p2", ["draft", "review"])
    resp = await chat_bot.answer_question("What's the status of p2?")
    assert resp == "p2 is currently in the draft phase."


@pytest.mark.asyncio
async def test_user_workload() -> None:
    add_project(ProjectModel(id="p3", name="Demo3", user="bob"))
    add_project(ProjectModel(id="p4", name="Demo4", user="bob"))
    resp = await chat_bot.answer_question("What is the workload for bob?")
    assert resp == "bob has 2 projects assigned."


@pytest.mark.asyncio
async def test_template_suggestion() -> None:
    resp = await chat_bot.answer_question("Which template should I use for a business letter?")
    assert "Business Letter Template" in resp


@pytest.mark.asyncio
async def test_document_types() -> None:
    add_document_type(DocumentTypeModel(name="Test Doc", template="<h1>Test</h1>"))
    resp = await chat_bot.answer_question("What document types are available?")
    assert "Test Doc" in resp


@pytest.mark.asyncio
async def test_list_templates() -> None:
    resp = await chat_bot.answer_question("List available templates")
    assert "FAA Advisory Circular" in resp


@pytest.mark.asyncio
async def test_user_response_time() -> None:
    # Create a workflow and approval for testing
    add_project(ProjectModel(id="p5", name="Demo5"))
    workflow = create_workflow("p5", ["draft", "review"])

    # Create an approval
    due_at = datetime.now(timezone.utc) + timedelta(days=2)
    approval = create_approval(workflow.id, "charlie", due_at, "Test approval")

    # Approve it quickly (within a day)
    update_approval_state(approval.id, "approved")

    resp = await chat_bot.answer_question("How long does charlie take to respond?")
    # Should indicate a quick response time
    assert "day" in resp.lower() or "responds within" in resp.lower()


@pytest.mark.asyncio
async def test_overdue_projects() -> None:
    # This test would require setting up overdue projects
    # For now, we'll just test that the question is recognized
    resp = await chat_bot.answer_question("How many overdue projects are there?")
    assert "overdue" in resp.lower()


@pytest.mark.asyncio
async def test_general_question() -> None:
    resp = await chat_bot.answer_question("What is DocReview360?")
    assert "document review and approval workflow system" in resp


@pytest.mark.asyncio
async def test_repo_content_question() -> None:
    resp = await chat_bot.answer_question(
        "Where can I find information about the FastAPI backend in DocReview360?"
    )
    assert "readme" in resp.lower()


@pytest.mark.asyncio
async def test_writing_style_question() -> None:
    resp = await chat_bot.answer_question("How should I handle passive voice in writing?")
    assert "active voice" in resp.lower()


@pytest.mark.asyncio
async def test_unknown_question() -> None:
    resp = await chat_bot.answer_question("What is the meaning of life?")
    assert "I can help answer questions about DocReview360" in resp
