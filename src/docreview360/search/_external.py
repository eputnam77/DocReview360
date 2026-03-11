# SPDX-License-Identifier: MIT
"""External full-text search client stub for OpenSearch / Elasticsearch.

When ``DOCREVIEW360_SEARCH_BACKEND`` is set to ``"opensearch"`` or
``"elasticsearch"`` and the corresponding URL env var is configured, this
module provides a thin HTTP client that delegates search indexing and queries
to the external cluster.

Default backend is ``"sqlite"`` (built-in FTS), in which case
:func:`is_external_search_configured` returns ``False`` and all
:class:`ExternalSearchClient` methods raise :exc:`NotImplementedError`.
"""

from __future__ import annotations

import logging
import os
from typing import Any

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

_EXTERNAL_BACKENDS = {"opensearch", "elasticsearch"}


def is_external_search_configured() -> bool:
    """Return ``True`` when an external search backend is fully configured.

    Both the ``DOCREVIEW360_SEARCH_BACKEND`` env var and the corresponding
    URL env var (``OPENSEARCH_URL`` or ``ELASTICSEARCH_URL``) must be set and
    non-empty.
    """
    backend = os.getenv("DOCREVIEW360_SEARCH_BACKEND", "sqlite").strip().lower()
    if backend not in _EXTERNAL_BACKENDS:
        return False
    if backend == "opensearch":
        return bool(os.getenv("OPENSEARCH_URL", "").strip())
    if backend == "elasticsearch":
        return bool(os.getenv("ELASTICSEARCH_URL", "").strip())
    return False


def get_search_backend() -> str:
    """Return the configured search backend name (lower-cased)."""
    return os.getenv("DOCREVIEW360_SEARCH_BACKEND", "sqlite").strip().lower()


def get_external_url() -> str | None:
    """Return the URL for the configured external search cluster, or ``None``."""
    backend = get_search_backend()
    if backend == "opensearch":
        url = os.getenv("OPENSEARCH_URL", "").strip()
        return url or None
    if backend == "elasticsearch":
        url = os.getenv("ELASTICSEARCH_URL", "").strip()
        return url or None
    return None


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class ExternalSearchClient:
    """Thin HTTP client for an OpenSearch or Elasticsearch cluster.

    Parameters
    ----------
    base_url:
        Root URL of the search cluster (e.g. ``https://localhost:9200``).
    index:
        Elasticsearch/OpenSearch index name.  Defaults to ``"docreview360"``.
    username:
        Optional HTTP Basic auth username.
    password:
        Optional HTTP Basic auth password.
    timeout:
        HTTP request timeout in seconds.  Defaults to 10.

    When instantiated without arguments the class reads configuration from
    environment variables via :func:`get_external_url`.  If no external URL is
    configured a :exc:`NotImplementedError` is raised.
    """

    def __init__(
        self,
        base_url: str | None = None,
        *,
        index: str = "docreview360",
        username: str | None = None,
        password: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        resolved_url = base_url or get_external_url()
        if not resolved_url:
            raise NotImplementedError(
                "No external search backend configured. "
                "Set DOCREVIEW360_SEARCH_BACKEND and OPENSEARCH_URL or ELASTICSEARCH_URL."
            )
        self.base_url = resolved_url.rstrip("/")
        self.index = index
        self.timeout = timeout
        self._auth: tuple[str, str] | None = (
            (username, password) if username and password else None  # type: ignore[assignment]
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _client(self) -> Any:
        """Return a configured :mod:`httpx` synchronous client."""
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover
            raise ImportError("httpx is required for external search. Install it with: pip install httpx") from exc
        kwargs: dict[str, Any] = {"timeout": self.timeout}
        if self._auth:
            kwargs["auth"] = self._auth
        return httpx.Client(**kwargs)

    def _index_url(self, doc_id: str | None = None) -> str:
        base = f"{self.base_url}/{self.index}/_doc"
        if doc_id:
            return f"{base}/{doc_id}"
        return base

    def _search_url(self) -> str:
        return f"{self.base_url}/{self.index}/_search"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        *,
        filters: dict[str, Any] | None = None,
        size: int = 20,
    ) -> list[dict[str, Any]]:
        """Run a full-text search against the external cluster.

        Parameters
        ----------
        query:
            Free-text search string.
        filters:
            Optional dict of field → value constraints added as ``filter``
            terms in the bool query.
        size:
            Maximum number of hits to return.

        Returns
        -------
        list[dict]
            Each element is the ``_source`` dict of a matching document.
        """
        must: list[dict[str, Any]] = [{"match": {"content": query}}] if query.strip() else []
        filter_clauses: list[dict[str, Any]] = []
        for field, value in (filters or {}).items():
            filter_clauses.append({"term": {field: value}})

        body: dict[str, Any] = {
            "size": size,
            "query": {"bool": {"must": must, "filter": filter_clauses}},
        }
        with self._client() as client:
            resp = client.post(self._search_url(), json=body)
            resp.raise_for_status()
            data = resp.json()
        hits = data.get("hits", {}).get("hits", [])
        return [hit["_source"] for hit in hits]

    def index_document(self, doc: dict[str, Any]) -> dict[str, Any]:
        """Index (upsert) a document into the search cluster.

        Parameters
        ----------
        doc:
            Document dict.  Must contain an ``"id"`` key used as the
            document ID in the index.

        Returns
        -------
        dict
            The raw API response from the cluster.
        """
        doc_id = str(doc.get("id", ""))
        if not doc_id:
            raise ValueError("Document must have a non-empty 'id' field")
        with self._client() as client:
            resp = client.put(self._index_url(doc_id), json=doc)
            resp.raise_for_status()
            return resp.json()

    def delete_document(self, doc_id: str) -> dict[str, Any]:
        """Remove a document from the search index.

        Parameters
        ----------
        doc_id:
            The document ID to delete.

        Returns
        -------
        dict
            The raw API response from the cluster.
        """
        if not doc_id:
            raise ValueError("doc_id must not be empty")
        with self._client() as client:
            resp = client.delete(self._index_url(doc_id))
            resp.raise_for_status()
            return resp.json()

    def ping(self) -> bool:
        """Return ``True`` if the cluster is reachable."""
        try:
            with self._client() as client:
                resp = client.get(self.base_url)
                return resp.status_code < 500
        except Exception:
            return False
