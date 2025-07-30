"""Utilities for text rewriting and summarization via OpenAI."""

from __future__ import annotations

import os

import httpx

from .ai_utils import synth_compress

__all__ = [
    "_call_openai",
    "rewrite_text",
    "summarize_text",
    "httpx",
]

OPENAI_KEY = os.getenv("OPENAI_KEY")


async def _call_openai(prompt: str) -> str:
    """Return completion text for ``prompt`` using ChatGPT.

    If ``OPENAI_KEY`` is not set the prompt is returned reversed so tests
    can run without network calls.
    """
    if not prompt.strip():
        raise ValueError("prompt is required")
    prompt = synth_compress(prompt)
    if not OPENAI_KEY:
        return " ".join(reversed(prompt.split()))

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_KEY}"},
                json={"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": prompt}]},
            )
            resp.raise_for_status()
    except httpx.HTTPError as exc:  # pragma: no cover - network errors
        raise RuntimeError("OpenAI request failed") from exc
    data = resp.json()
    return str(data.get("choices", [{}])[0].get("message", {}).get("content", "")).strip()


async def rewrite_text(text: str) -> str:
    """Return a rewritten version of ``text`` via ChatGPT."""
    if not text.strip():
        raise ValueError("text is required")
    prompt = f"Rewrite the following text in clear English:\n{text}"
    return await _call_openai(prompt)


async def summarize_text(text: str) -> str:
    """Return a one sentence summary of ``text`` via ChatGPT."""
    if not text.strip():
        raise ValueError("text is required")
    prompt = f"Summarize the following text in one sentence:\n{text}"
    return await _call_openai(prompt)
