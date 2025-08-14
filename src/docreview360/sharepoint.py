"""Microsoft SharePoint integration via Microsoft Graph API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import requests

_GRAPH_URL = "https://graph.microsoft.com/v1.0"


@dataclass
class SharePointClient:
    """Minimal SharePoint client supporting upload, download and versioning."""

    site_id: str
    drive_id: str
    token: str

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def upload_file(self, path: str, data: bytes) -> str:
        """Upload ``data`` to ``path`` returning the created item id."""
        url = f"{_GRAPH_URL}/sites/{self.site_id}/drives/{self.drive_id}/root:/{path}:/content"
        response = requests.put(url, headers=self._headers(), data=data)
        response.raise_for_status()
        payload = response.json()
        item_id = payload.get("id")
        if not isinstance(item_id, str):  # pragma: no cover - defensive
            raise ValueError("Missing item id in SharePoint response")
        return item_id

    def download_file(self, item_id: str) -> bytes:
        """Return the bytes of the file ``item_id``."""
        url = f"{_GRAPH_URL}/sites/{self.site_id}/drives/{self.drive_id}/items/{item_id}/content"
        response = requests.get(url, headers=self._headers())
        response.raise_for_status()
        return response.content

    def list_versions(self, item_id: str) -> List[str]:
        """Return version identifiers for ``item_id``."""
        url = f"{_GRAPH_URL}/sites/{self.site_id}/drives/{self.drive_id}/items/{item_id}/versions"
        response = requests.get(url, headers=self._headers())
        response.raise_for_status()
        payload = response.json()
        values = payload.get("value", [])
        return [str(entry.get("id")) for entry in values if "id" in entry]
