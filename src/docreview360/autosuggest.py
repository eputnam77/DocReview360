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
        data = resp.json()["suggest"][0]["options"]

    record_task_completion(135)
    return [Suggestion(text=o["text"], score=o.get("_score", 0.0)) for o in data]
