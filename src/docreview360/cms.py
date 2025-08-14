"""CMS persistence helpers."""

from __future__ import annotations

import os
from typing import Optional

from .config import Config
from .documents import DocumentModel
from .exporter import export_document
from .sharepoint import SharePointClient


def save_to_cms(
    document: DocumentModel,
    *,
    config: Config,
    fmt: str = "markdown",
    client: Optional[SharePointClient] = None,
) -> str | None:
    """Persist ``document`` to the configured CMS.

    Currently only SharePoint is supported. The document is exported using
    :func:`export_document` and uploaded to SharePoint via
    :class:`SharePointClient`. The generated filename honours the
    ``Config.filename_template`` setting.

    Parameters
    ----------
    document:
        Document instance to save.
    config:
        Loaded application configuration.
    fmt:
        Export format, defaults to ``"markdown"``.
    client:
        Optional pre-configured :class:`SharePointClient` instance. When not
        provided credentials are read from ``SHAREPOINT_SITE_ID``,
        ``SHAREPOINT_DRIVE_ID`` and ``SHAREPOINT_TOKEN`` environment
        variables.

    Returns
    -------
    str | None
        The item id returned by SharePoint or ``None`` when no upload was
        performed because the CMS is not configured for SharePoint.
    """
    if config.cms.lower() != "sharepoint":
        return None

    if client is None:
        site_id = os.getenv("SHAREPOINT_SITE_ID")
        drive_id = os.getenv("SHAREPOINT_DRIVE_ID")
        token = os.getenv("SHAREPOINT_TOKEN")
        if not all([site_id, drive_id, token]):
            raise ValueError("Missing SharePoint credentials")
        client = SharePointClient(site_id=site_id, drive_id=drive_id, token=token)

    data, _, filename = export_document(document, fmt, name_template=config.filename_template)
    return client.upload_file(filename, data)
