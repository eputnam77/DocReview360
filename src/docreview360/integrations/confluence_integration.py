# SPDX-License-Identifier: MIT
"""Confluence Cloud and Data Center integration.

Provides read and write operations against the Confluence REST API v2,
including space listing, page import/export, and attachment uploads.

Configuration environment variables:
- ``CONFLUENCE_BASE_URL``   — e.g. ``https://myorg.atlassian.net/wiki``
- ``CONFLUENCE_USERNAME``   — Atlassian account email (Cloud) or username (DC)
- ``CONFLUENCE_API_TOKEN``  — API token (Cloud) or password (Data Center)
- ``CONFLUENCE_SPACE_KEY``  — default space key for import/export operations
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass, field
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen


@dataclass
class ConfluencePage:
    """Lightweight representation of a Confluence page."""

    id: str
    title: str
    space_key: str
    body_storage: str
    version: int
    url: str = ""
    labels: list[str] = field(default_factory=list)


@dataclass
class ConfluenceClient:
    """Thin wrapper around the Confluence REST API.

    Instantiate via :func:`client_from_env` to read credentials from the
    environment automatically.
    """

    base_url: str
    username: str
    api_token: str
    space_key: str = ""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _auth_header(self) -> str:
        token = base64.b64encode(f"{self.username}:{self.api_token}".encode()).decode()
        return f"Basic {token}"

    def _request(
        self,
        method: str,
        path: str,
        payload: Any = None,
        params: dict[str, str] | None = None,
    ) -> Any:
        url = urljoin(self.base_url.rstrip("/") + "/", path.lstrip("/"))
        if params:
            url = f"{url}?{urlencode(params)}"
        data: bytes | None = None
        headers: dict[str, str] = {
            "Authorization": self._auth_header(),
            "Accept": "application/json",
        }
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        req = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=30) as resp:
                body = resp.read()
                return json.loads(body) if body else {}
        except HTTPError as exc:
            raise ConfluenceError(f"HTTP {exc.code} from Confluence: {exc.reason}") from exc
        except URLError as exc:
            raise ConfluenceError(f"Cannot reach Confluence at {self.base_url}: {exc.reason}") from exc

    # ------------------------------------------------------------------
    # Space operations
    # ------------------------------------------------------------------

    def list_spaces(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return a list of accessible Confluence spaces."""
        resp = self._request("GET", "/rest/api/v2/spaces", params={"limit": str(limit)})
        return resp.get("results", [])

    def get_space(self, space_key: str) -> dict[str, Any]:
        """Return metadata for a single space by key."""
        return self._request("GET", f"/rest/api/space/{space_key}")

    # ------------------------------------------------------------------
    # Page operations
    # ------------------------------------------------------------------

    def get_page(self, page_id: str) -> ConfluencePage:
        """Fetch a page by its numeric ID and return a :class:`ConfluencePage`."""
        resp = self._request(
            "GET",
            f"/rest/api/v2/pages/{page_id}",
            params={"body-format": "storage"},
        )
        return _parse_page(resp)

    def search_pages(self, query: str, space_key: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
        """Full-text search using Confluence Query Language (CQL)."""
        cql = f'text ~ "{query}" AND type = page'
        if space_key:
            cql += f' AND space = "{space_key}"'
        resp = self._request(
            "GET",
            "/rest/api/content/search",
            params={"cql": cql, "limit": str(limit)},
        )
        return resp.get("results", [])

    def create_page(
        self,
        title: str,
        body_html: str,
        space_key: str | None = None,
        parent_id: str | None = None,
    ) -> ConfluencePage:
        """Create a new page and return the resulting :class:`ConfluencePage`."""
        space_key = space_key or self.space_key
        if not space_key:
            raise ConfluenceError("space_key is required to create a page")
        payload: dict[str, Any] = {
            "title": title,
            "type": "page",
            "space": {"key": space_key},
            "body": {"storage": {"value": body_html, "representation": "storage"}},
        }
        if parent_id:
            payload["ancestors"] = [{"id": parent_id}]
        resp = self._request("POST", "/rest/api/content", payload)
        return _parse_page(resp)

    def update_page(self, page_id: str, title: str, body_html: str, version: int) -> ConfluencePage:
        """Update an existing page to a new version."""
        payload = {
            "id": page_id,
            "type": "page",
            "title": title,
            "version": {"number": version + 1},
            "body": {"storage": {"value": body_html, "representation": "storage"}},
        }
        resp = self._request("PUT", f"/rest/api/content/{page_id}", payload)
        return _parse_page(resp)

    def delete_page(self, page_id: str) -> bool:
        """Move a page to the trash. Returns True on success."""
        self._request("DELETE", f"/rest/api/content/{page_id}")
        return True

    # ------------------------------------------------------------------
    # Import / export helpers
    # ------------------------------------------------------------------

    def export_page_as_markdown(self, page_id: str) -> str:
        """Fetch a page and convert its storage-format body to Markdown.

        The conversion is intentionally minimal — strip common Confluence
        XHTML macro tags, replace headings, bold, and links.
        """
        page = self.get_page(page_id)
        return _storage_to_markdown(page.body_storage)

    def import_document(
        self,
        title: str,
        content: str,
        space_key: str | None = None,
        parent_id: str | None = None,
        content_format: str = "markdown",
    ) -> ConfluencePage:
        """Import a document into Confluence.

        *content_format* may be ``"markdown"`` (converted to storage format)
        or ``"storage"`` (used as-is).
        """
        if content_format == "markdown":
            body_html = _markdown_to_storage(content)
        else:
            body_html = content
        return self.create_page(title, body_html, space_key=space_key, parent_id=parent_id)


# ---------------------------------------------------------------------------
# Module-level convenience factory
# ---------------------------------------------------------------------------


class ConfluenceError(RuntimeError):
    """Raised when a Confluence API call fails."""


def client_from_env() -> ConfluenceClient:
    """Return a :class:`ConfluenceClient` configured from environment variables."""
    base_url = os.environ.get("CONFLUENCE_BASE_URL", "")
    username = os.environ.get("CONFLUENCE_USERNAME", "")
    api_token = os.environ.get("CONFLUENCE_API_TOKEN", "")
    space_key = os.environ.get("CONFLUENCE_SPACE_KEY", "")
    if not base_url:
        raise ConfluenceError("CONFLUENCE_BASE_URL is not set")
    return ConfluenceClient(
        base_url=base_url,
        username=username,
        api_token=api_token,
        space_key=space_key,
    )


# ---------------------------------------------------------------------------
# Internal format helpers
# ---------------------------------------------------------------------------


def _parse_page(resp: dict[str, Any]) -> ConfluencePage:
    body = resp.get("body", {})
    storage = body.get("storage", body.get("storage", {}))
    body_storage = storage.get("value", "") if isinstance(storage, dict) else ""
    links = resp.get("_links", {})
    version_info = resp.get("version", {})
    space_info = resp.get("space", {})
    return ConfluencePage(
        id=str(resp.get("id", "")),
        title=resp.get("title", ""),
        space_key=space_info.get("key", ""),
        body_storage=body_storage,
        version=int(version_info.get("number", 1)),
        url=links.get("webui", ""),
    )


def _storage_to_markdown(storage_xml: str) -> str:
    """Very light conversion from Confluence storage format to Markdown."""
    import re
    text = storage_xml
    # Headings
    for n in range(6, 0, -1):
        text = re.sub(rf"<h{n}[^>]*>(.*?)</h{n}>", "#" * n + r" \1", text, flags=re.DOTALL)
    # Bold, italic
    text = re.sub(r"<strong>(.*?)</strong>", r"**\1**", text, flags=re.DOTALL)
    text = re.sub(r"<em>(.*?)</em>", r"*\1*", text, flags=re.DOTALL)
    # Links
    text = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r"[\2](\1)", text, flags=re.DOTALL)
    # Strip remaining tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode common XML entities
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'")
    return text.strip()


def _markdown_to_storage(markdown: str) -> str:
    """Minimal Markdown → Confluence storage format conversion."""
    import re
    text = markdown
    # Headings
    for n in range(6, 0, -1):
        text = re.sub(rf"^{'#' * n} (.+)$", rf"<h{n}>\1</h{n}>", text, flags=re.MULTILINE)
    # Bold, italic
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    # Links
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    # Paragraphs
    paragraphs = re.split(r"\n{2,}", text.strip())
    parts = []
    for para in paragraphs:
        para = para.strip()
        if para and not para.startswith("<h"):
            para = f"<p>{para}</p>"
        parts.append(para)
    return "\n".join(parts)
