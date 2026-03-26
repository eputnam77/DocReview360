# SPDX-License-Identifier: MIT
"""Google Drive integration for DocReview360.

Provides file listing, download, upload, and Google Docs export via the
Google Drive REST API v3.

Configuration environment variables:
- ``GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON``  — JSON key for a service account
  (inline JSON string or path to a .json file)
- ``GOOGLE_DRIVE_FOLDER_ID``            — default parent folder ID for uploads
- ``GOOGLE_DRIVE_SCOPE``                — comma-separated OAuth scopes
  (default: drive.readonly,drive.file)

OAuth2/PKCE for user-delegated flows is handled by the OIDC provider
(see ``oidc_client.py``); this module uses service-account credentials
suitable for server-side batch operations.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"
DRIVE_UPLOAD_BASE = "https://www.googleapis.com/upload/drive/v3"


class GoogleDriveError(RuntimeError):
    """Raised when a Google Drive API call fails."""


@dataclass
class DriveFile:
    """Lightweight representation of a Google Drive file."""

    id: str
    name: str
    mime_type: str
    size: int = 0
    modified_time: str = ""
    parents: list[str] = field(default_factory=list)
    web_view_link: str = ""


@dataclass
class GoogleDriveClient:
    """Authenticated client for the Google Drive REST API v3.

    Use :func:`client_from_env` to build from environment variables.
    """

    access_token: str
    default_folder_id: str = ""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        payload: Any = None,
        params: dict[str, str] | None = None,
        base_url: str = DRIVE_API_BASE,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        url = f"{base_url}/{path.lstrip('/')}"
        if params:
            url = f"{url}?{urlencode(params)}"
        data: bytes | None = None
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)
        if payload is not None and isinstance(payload, dict):
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        elif payload is not None and isinstance(payload, bytes):
            data = payload
        req = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=60) as resp:
                body = resp.read()
                return json.loads(body) if body else {}
        except HTTPError as exc:
            raise GoogleDriveError(
                f"Google Drive API error {exc.code}: {exc.reason}"
            ) from exc
        except URLError as exc:
            raise GoogleDriveError(
                f"Cannot reach Google Drive API: {exc.reason}"
            ) from exc

    # ------------------------------------------------------------------
    # File listing
    # ------------------------------------------------------------------

    def list_files(
        self,
        folder_id: str | None = None,
        query: str | None = None,
        page_size: int = 50,
        fields: str = "files(id,name,mimeType,size,modifiedTime,parents,webViewLink)",
    ) -> list[DriveFile]:
        """List files in *folder_id* (or all accessible files if omitted)."""
        q_parts: list[str] = ["trashed = false"]
        if folder_id:
            q_parts.append(f"'{folder_id}' in parents")
        if query:
            q_parts.append(f"name contains '{query}'")
        params: dict[str, str] = {
            "q": " and ".join(q_parts),
            "pageSize": str(page_size),
            "fields": fields,
        }
        resp = self._request("GET", "files", params=params)
        return [_parse_file(f) for f in resp.get("files", [])]

    def search_files(self, query: str, page_size: int = 25) -> list[DriveFile]:
        """Full-text search across Drive contents."""
        return self.list_files(query=query, page_size=page_size)

    def get_file_metadata(self, file_id: str) -> DriveFile:
        """Return metadata for a single file by ID."""
        resp = self._request(
            "GET",
            f"files/{file_id}",
            params={"fields": "id,name,mimeType,size,modifiedTime,parents,webViewLink"},
        )
        return _parse_file(resp)

    # ------------------------------------------------------------------
    # Download / export
    # ------------------------------------------------------------------

    def download_file(self, file_id: str) -> bytes:
        """Download a binary file and return its raw bytes."""
        url = f"{DRIVE_API_BASE}/files/{file_id}?alt=media"
        req = Request(url, headers={"Authorization": f"Bearer {self.access_token}"})
        try:
            with urlopen(req, timeout=120) as resp:
                return resp.read()
        except HTTPError as exc:
            raise GoogleDriveError(f"Download failed: {exc.code} {exc.reason}") from exc

    def export_google_doc(self, file_id: str, mime_type: str = "text/plain") -> bytes:
        """Export a Google Docs/Sheets/Slides file to a non-Google MIME type.

        Common *mime_type* values:
        - ``"text/plain"`` — plain text (Docs)
        - ``"application/pdf"`` — PDF (any format)
        - ``"application/vnd.openxmlformats-officedocument.wordprocessingml.document"`` — DOCX
        - ``"text/csv"`` — CSV (Sheets)
        """
        url = f"{DRIVE_API_BASE}/files/{file_id}/export?mimeType={mime_type}"
        req = Request(url, headers={"Authorization": f"Bearer {self.access_token}"})
        try:
            with urlopen(req, timeout=120) as resp:
                return resp.read()
        except HTTPError as exc:
            raise GoogleDriveError(f"Export failed: {exc.code} {exc.reason}") from exc

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    def upload_file(
        self,
        name: str,
        content: bytes,
        mime_type: str = "application/octet-stream",
        folder_id: str | None = None,
    ) -> DriveFile:
        """Upload *content* as a new file in Drive using multipart upload.

        Returns the newly created :class:`DriveFile`.
        """
        folder_id = folder_id or self.default_folder_id
        metadata: dict[str, Any] = {"name": name}
        if folder_id:
            metadata["parents"] = [folder_id]

        # Multipart boundary
        boundary = "DriveReview360Boundary"
        meta_bytes = json.dumps(metadata).encode()
        body = (
            f"--{boundary}\r\n"
            f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
        ).encode()
        body += meta_bytes
        body += f"\r\n--{boundary}\r\nContent-Type: {mime_type}\r\n\r\n".encode()
        body += content
        body += f"\r\n--{boundary}--".encode()

        url = f"{DRIVE_UPLOAD_BASE}/files?uploadType=multipart&fields=id,name,mimeType,size,modifiedTime,parents,webViewLink"
        req = Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": f"multipart/related; boundary={boundary}",
            },
            method="POST",
        )
        try:
            with urlopen(req, timeout=120) as resp:
                return _parse_file(json.loads(resp.read()))
        except HTTPError as exc:
            raise GoogleDriveError(f"Upload failed: {exc.code} {exc.reason}") from exc

    def update_file(self, file_id: str, content: bytes, mime_type: str = "application/octet-stream") -> DriveFile:
        """Replace the content of an existing Drive file."""
        url = f"{DRIVE_UPLOAD_BASE}/files/{file_id}?uploadType=media&fields=id,name,mimeType,size,modifiedTime"
        req = Request(
            url,
            data=content,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": mime_type,
            },
            method="PATCH",
        )
        try:
            with urlopen(req, timeout=120) as resp:
                return _parse_file(json.loads(resp.read()))
        except HTTPError as exc:
            raise GoogleDriveError(f"Update failed: {exc.code} {exc.reason}") from exc

    def delete_file(self, file_id: str) -> bool:
        """Permanently delete a file. Returns True on success."""
        self._request("DELETE", f"files/{file_id}")
        return True

    # ------------------------------------------------------------------
    # Permissions (sharing)
    # ------------------------------------------------------------------

    def share_file(self, file_id: str, email: str, role: str = "reader") -> dict[str, Any]:
        """Share *file_id* with *email* at the given *role* (reader/writer/commenter)."""
        payload = {"type": "user", "role": role, "emailAddress": email}
        return self._request("POST", f"files/{file_id}/permissions", payload)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def client_from_env() -> GoogleDriveClient:
    """Return a :class:`GoogleDriveClient` using service account credentials.

    Exchanges the service account key for a short-lived access token via
    the Google OAuth 2.0 token endpoint.  Requires the ``google-auth``
    library if the full JWT signing flow is used; otherwise raises a
    :class:`GoogleDriveError` with instructions.

    In tests / CI without network access, set ``GOOGLE_DRIVE_ACCESS_TOKEN``
    directly to skip the OAuth exchange.
    """
    direct_token = os.environ.get("GOOGLE_DRIVE_ACCESS_TOKEN")
    if direct_token:
        return GoogleDriveClient(
            access_token=direct_token,
            default_folder_id=os.environ.get("GOOGLE_DRIVE_FOLDER_ID", ""),
        )

    sa_json_env = os.environ.get("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON", "")
    if not sa_json_env:
        raise GoogleDriveError(
            "Set GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON (inline JSON or file path) "
            "or GOOGLE_DRIVE_ACCESS_TOKEN to use the Google Drive integration."
        )

    try:
        sa_info: dict[str, Any] = json.loads(sa_json_env)
    except json.JSONDecodeError:
        # Treat as file path
        with open(sa_json_env) as fh:
            sa_info = json.load(fh)

    access_token = _get_service_account_token(sa_info)
    return GoogleDriveClient(
        access_token=access_token,
        default_folder_id=os.environ.get("GOOGLE_DRIVE_FOLDER_ID", ""),
    )


def _get_service_account_token(sa_info: dict[str, Any]) -> str:
    """Exchange a service-account key for a Bearer token.

    Uses ``google-auth`` if available; raises :class:`GoogleDriveError` with
    a helpful message if the library is not installed.
    """
    try:
        import google.auth.transport.requests  # type: ignore[import]
        from google.oauth2 import service_account  # type: ignore[import]

        scopes = ["https://www.googleapis.com/auth/drive"]
        creds = service_account.Credentials.from_service_account_info(sa_info, scopes=scopes)
        creds.refresh(google.auth.transport.requests.Request())
        return creds.token  # type: ignore[return-value]
    except ImportError as exc:
        raise GoogleDriveError(
            "Install 'google-auth' to use service-account credentials: "
            "pip install google-auth"
        ) from exc


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_file(data: dict[str, Any]) -> DriveFile:
    return DriveFile(
        id=data.get("id", ""),
        name=data.get("name", ""),
        mime_type=data.get("mimeType", ""),
        size=int(data.get("size", 0)),
        modified_time=data.get("modifiedTime", ""),
        parents=data.get("parents", []),
        web_view_link=data.get("webViewLink", ""),
    )
