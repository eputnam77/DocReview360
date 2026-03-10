# SPDX-License-Identifier: MIT
"""Lightweight full-text search using SQLite FTS5.

This module is a simplified stand in for Postgres full-text search so tests can
exercise search logic without requiring an external database.  Documents are
stored in an in-memory virtual table and queried using the ``MATCH`` operator.
"""

from __future__ import annotations

import sqlite3
from typing import List

_conn = sqlite3.connect(":memory:", check_same_thread=False)
_conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5(id, content)")


def index_document(doc_id: str, content: str) -> None:
    """Index ``content`` under ``doc_id``.

    Raises
    ------
    ValueError
        If either argument is empty.
    """
    doc_id = doc_id.strip()
    content = content.strip()
    if not doc_id or not content:
        raise ValueError("doc_id and content are required")
    # ``fts5`` tables happily accept multiple rows with the same ``id``
    # which would cause searches to return duplicate document identifiers
    # when re-indexing existing documents. The real system performs an
    # upsert so repeated indexing replaces the previous content. Mirror
    # that behavior here with the FTS5-supported upsert form by targeting
    # the existing rowid for the document id.
    _conn.execute(
        "INSERT OR REPLACE INTO docs (rowid, id, content) "
        "VALUES ((SELECT rowid FROM docs WHERE id = ?), ?, ?)",
        (doc_id, doc_id, content),
    )


def search(query: str) -> List[str]:
    """Return document ids matching ``query``."""
    if not query.strip():
        raise ValueError("query must not be empty")
    rows = _conn.execute("SELECT id FROM docs WHERE docs MATCH ?", (query,))
    return [row[0] for row in rows]


def remove_document(doc_id: str) -> None:
    """Remove a document from the index."""
    doc_id = doc_id.strip()
    if not doc_id:
        raise ValueError("doc_id required")
    _conn.execute("DELETE FROM docs WHERE id = ?", (doc_id,))


def clear() -> None:
    """Remove all indexed documents."""
    _conn.execute("DELETE FROM docs")
