"""Semantic search auto-suggest helper."""

from typing import cast

from pydantic import HttpUrl

from ..autosuggest import suggest


async def task135(host: str) -> list[str]:
    """Return suggestion strings from OpenSearch."""
    results = await suggest(cast(HttpUrl, host), "test")
    return [r.text for r in results]
