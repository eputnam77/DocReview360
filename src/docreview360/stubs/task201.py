"""Tiny AI chat bot demo."""

from __future__ import annotations

from ..stubs import record_task_completion

_ANSWERS = {
    "status": "All projects are on track.",
    "who": "The current assignee is Alice.",
}


def task201(question: str) -> str:
    """Return a canned response for ``question``.

    Parameters
    ----------
    question:
        User prompt in natural language.
    """

    record_task_completion(201)
    for key, answer in _ANSWERS.items():
        if key in question.lower():
            return answer
    return "I don't know."
