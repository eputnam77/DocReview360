import pytest

from docreview360 import chat_bot
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
async def test_unknown_question() -> None:
    resp = await chat_bot.answer_question("What is the meaning of life?")
    assert resp == "I don't know."
