"""Utilities for text rewriting and summarization via OpenAI."""

from __future__ import annotations

import httpx

from .ai_utils import synth_compress
from .secrets import get_secret

__all__ = [
    "_call_openai",
    "rewrite_text",
    "summarize_text",
    "httpx",
]


# ``tests.test_ai_assist`` relies on being able to monkeypatch the OpenAI
# authentication key at module level.  The original implementation looked up
# the secret on every call which meant the module had no ``OPENAI_KEY``
# attribute and the tests failed with ``AttributeError``.  Storing the key in a
# module level variable keeps the behavior identical (it's still loaded from
# ``get_secret`` at import time) while allowing tests and callers to override it
# easily.

# The key is resolved at import time so the default behavior is unchanged – if
# the secret is missing the fallback behavior (reversing the prompt) is still
# triggered.
OPENAI_KEY = get_secret("openai")


async def _call_openai(prompt: str) -> str:
    """Return completion text for ``prompt`` using ChatGPT.

    If the OpenAI token is unavailable the prompt is returned reversed so tests
    can run without network calls.
    """
    if not prompt.strip():
        raise ValueError("prompt is required")
    prompt = synth_compress(prompt)
    # ``OPENAI_KEY`` is resolved at import time and may be monkeypatched during
    # tests.  Using the module level variable avoids repeated secret lookups and
    # mirrors the behavior expected by the tests.
    key = OPENAI_KEY
    if not key:
        return " ".join(reversed(prompt.split()))

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": prompt}]},
            )
            resp.raise_for_status()
    except httpx.HTTPError as exc:
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
