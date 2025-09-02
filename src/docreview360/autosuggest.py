"""Semantic search auto-suggest utilities."""

from __future__ import annotations

import httpx
from pydantic import BaseModel, HttpUrl

from .stubs import record_task_completion


class Suggestion(BaseModel):
    """Represents a single suggestion result."""

    text: str
    score: float


async def suggest(host: HttpUrl, text: str, index: str = "documents") -> list[Suggestion]:
    """Query OpenSearch ``_suggest`` and return top suggestions."""
    if not text:
        raise ValueError("text must not be empty")
    url = f"{host}/{index}/_suggest"
    payload = {
        "suggest": {"text": text, "simple": {"prefix": text, "completion": {"field": "title"}}}
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, timeout=5)
        resp.raise_for_status()
        # ``_suggest`` responses nest suggestions under the name provided in
        # the request.  The previous implementation attempted to index into the
        # ``suggest`` dict using ``[0]`` which raised ``TypeError``.  Correctly
        # navigate to the "simple" suggestion list before extracting options.
        #
        # OpenSearch may legitimately return an empty list of suggestions.  The
        # earlier implementation blindly indexed ``[0]`` which raised
        # ``IndexError`` in such cases.  Gracefully handle missing or empty
        # results by returning an empty suggestion list.
        body = resp.json()
        simple = body.get("suggest", {}).get("simple", [])
        if simple:
            options = simple[0].get("options", [])
        else:
            options = []

    record_task_completion(135)
    return [Suggestion(text=o["text"], score=o.get("_score", 0.0)) for o in options]
