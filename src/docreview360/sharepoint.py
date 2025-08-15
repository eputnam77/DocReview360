"""Microsoft SharePoint integration via Microsoft Graph API."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, cast

import requests  # type: ignore[import-untyped]

from .approvals import submit_draft_for_approval
from .fann_model import Weights
from .quality import approval_likelihood
from .reviewer_model import ReviewerModel

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
        return cast(bytes, response.content)

    def list_versions(self, item_id: str) -> List[str]:
        """Return version identifiers for ``item_id``."""
        url = f"{_GRAPH_URL}/sites/{self.site_id}/drives/{self.drive_id}/items/{item_id}/versions"
        response = requests.get(url, headers=self._headers())
        response.raise_for_status()
        payload = response.json()
        values = payload.get("value", [])
        return [str(entry.get("id")) for entry in values if "id" in entry]

    def set_properties(self, item_id: str, properties: dict[str, str]) -> None:
        """Update SharePoint item metadata properties."""
        url = (
            f"{_GRAPH_URL}/sites/{self.site_id}/drives/{self.drive_id}/"
            f"items/{item_id}/listItem/fields"
        )
        headers = self._headers()
        headers["Content-Type"] = "application/json"
        response = requests.patch(url, headers=headers, json=properties)
        response.raise_for_status()

    def upload_with_scoring(
        self,
        path: str,
        data: bytes,
        weights: Weights,
        *,
        workflow: str | None = None,
        reviewer: str | None = "manager",
        extra_reviewer: str = "policy",
        threshold: float = 0.5,
        reviewer_model: ReviewerModel | None = None,
    ) -> tuple[str, float]:
        """Upload ``data`` and route for approval based on FANN scoring.

        The uploaded document is scored using ``weights``.  If the approval
        likelihood is below ``threshold`` an extra review step is inserted prior
        to the normal ``reviewer``.
        """

        item_id = self.upload_file(path, data)
        text = data.decode("utf-8", errors="ignore")
        score = approval_likelihood(text, weights)
        if workflow is not None:
            submit_draft_for_approval(
                workflow,
                reviewer,
                item_id,
                text,
                weights,
                threshold=threshold,
                extra_reviewer=extra_reviewer,
                reviewer_model=reviewer_model,
            )
        return item_id, score


def client_from_env() -> SharePointClient:
    """Return a :class:`SharePointClient` using environment credentials."""
    site_id = os.getenv("SHAREPOINT_SITE_ID")
    drive_id = os.getenv("SHAREPOINT_DRIVE_ID")
    token = os.getenv("SHAREPOINT_TOKEN")
    if not all([site_id, drive_id, token]):
        raise ValueError("Missing SharePoint credentials")
    return SharePointClient(
        site_id=cast(str, site_id),
        drive_id=cast(str, drive_id),
        token=cast(str, token),
    )
