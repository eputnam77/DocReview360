"""Wrapper for the GraphQL read layer used in task 88."""

from __future__ import annotations

from .. import graphql_api
from . import record_task_completion


def execute_query(query: str) -> dict[str, object]:
    """Proxy to ``graphql_api.execute_query`` and record completion."""
    if not query:
        raise ValueError("query is required")
    record_task_completion(88)
    return graphql_api.execute_query(query)
