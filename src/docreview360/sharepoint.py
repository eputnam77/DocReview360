"""Microsoft SharePoint integration via Microsoft Graph API."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, cast

import requests  # type: ignore[import-untyped]

from .approvals import create_approval, submit_draft_for_approval
from .ml.features import routing_features
from .quality import QUALITY_FLAG_NAMES, quality_assessment
from .reviewer_model import ReviewerModel
from .secrets import get_secret

if TYPE_CHECKING:
    from .ml.torch_models import TinyCritic

_GRAPH_URL = "https://graph.microsoft.com/v1.0"


@dataclass
class SharePointClient:
    """Minimal SharePoint client supporting upload, download, metadata, and versioning."""

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
        ids: List[str] = []
        for entry in values:
            entry_id = entry.get("id")
            if isinstance(entry_id, (str, int)):
                ids.append(str(entry_id))
        return ids

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
        critic: "TinyCritic | None" = None,
        *,
        workflow: str | None = None,
        reviewer: str | None = None,
        extra_reviewer: str = "policy",
        threshold: float = 0.5,
        reviewer_model: ReviewerModel | None = None,
    ) -> tuple[str, float, list[str]]:
        """Upload ``data`` and route for approval based on FANN scoring.

        Returns:
            tuple[item_id, score, approval_ids]
            approval_ids is a list of all created approval IDs (may be empty).
        """
        # Upload the document
        item_id = self.upload_file(path, data)

        # Calculate quality score via ONNX critic
        text = data.decode("utf-8", errors="ignore")
        assessment = quality_assessment(text)
        score = assessment.score
        routing = routing_features(text, {"workflow": workflow} if workflow else None)[
            "features"
        ]

        approval_ids: list[str] = []

        # Trigger workflow approvals if configured
        if workflow is not None:
            if reviewer_model:
                approval = submit_draft_for_approval(
                    workflow,
                    reviewer,
                    item_id,
                    text,
                    critic,
                    threshold=threshold,
                    extra_reviewer=extra_reviewer,
                    reviewer_model=reviewer_model,
                )
                if approval:
                    approval_ids.append(approval.id)
            else:
                if score < threshold:
                    approval = create_approval(
                        workflow,
                        extra_reviewer,
                        doc_id=item_id,
                        description=f"Auto risk review (threshold {threshold:.2f})",
                    )
                    if approval:
                        approval_ids.append(approval.id)
                approval = create_approval(
                    workflow,
                    reviewer or "manager",
                    doc_id=item_id,
                    description=f"Primary review (threshold {threshold:.2f})",
                )
                if approval:
                    approval_ids.append(approval.id)

        # Auto-tag SharePoint with workflow + scoring info
        flag_pairs = [
            f"{name}:{value:.3f}" for name, value in zip(QUALITY_FLAG_NAMES, assessment.flags)
        ]
        metadata = {
            "Workflow": workflow or "",
            "QualityScore": f"{score:.3f}",
            "QualityFlags": ", ".join(flag_pairs) if flag_pairs else "",
            "QualityThreshold": f"{threshold:.3f}",
            "ApprovalIDs": ", ".join(approval_ids) if approval_ids else "",
            "RoutePriority": f"{routing['priority']:.3f}",
            "StructureScore": f"{routing['structure']:.3f}",
        }
        try:
            self.set_properties(item_id, metadata)
        except Exception as e:
            # We don't want metadata failures to block main flow
            print(f"Warning: Failed to set SharePoint metadata for {item_id}: {e}")

        return item_id, score, approval_ids


def client_from_env() -> SharePointClient:
    """Return a :class:`SharePointClient` using configured credentials."""
    site_id = os.getenv("SHAREPOINT_SITE_ID")
    drive_id = os.getenv("SHAREPOINT_DRIVE_ID")
    token = get_secret("sharepoint")
    if not all([site_id, drive_id, token]):
        raise ValueError("Missing SharePoint credentials")
    return SharePointClient(
        site_id=cast(str, site_id),
        drive_id=cast(str, drive_id),
        token=cast(str, token),
    )


class AsyncSharePointClient(SharePointClient):
    """Async wrapper for :class:`SharePointClient` using threads."""

    async def upload_file(self, path: str, data: bytes) -> str:  # pragma: no cover - thin wrapper
        return await asyncio.to_thread(super().upload_file, path, data)

    async def set_properties(
        self, item_id: str, properties: dict[str, str]
    ) -> None:  # pragma: no cover
        await asyncio.to_thread(super().set_properties, item_id, properties)


async def async_client_from_env() -> AsyncSharePointClient:
    """Return an async SharePoint client using environment credentials."""

    client = client_from_env()
    return AsyncSharePointClient(client.site_id, client.drive_id, client.token)


__all__ = [
    "SharePointClient",
    "client_from_env",
    "AsyncSharePointClient",
    "async_client_from_env",
]
