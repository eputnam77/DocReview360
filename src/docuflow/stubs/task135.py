"""Semantic search auto-suggest helper."""

from ..autosuggest import suggest


async def task135(host: str) -> list[str]:
    """Return suggestion strings from OpenSearch."""
    results = await suggest(host, "test")
    return [r.text for r in results]
