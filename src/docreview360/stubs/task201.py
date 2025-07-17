"""Tiny AI chat bot demo."""

from __future__ import annotations

from ..stubs import record_task_completion
from ..chat_bot import answer_question


async def task201(question: str) -> str:
    """Return a canned response for ``question``.

    Parameters
    ----------
    question:
        User prompt in natural language.
    """

    record_task_completion(201)
    return await answer_question(question)
