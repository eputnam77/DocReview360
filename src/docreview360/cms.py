"""CMS persistence helpers."""

from __future__ import annotations

from typing import Optional

from .config import Config
from .documents import DocumentModel
from .exporter import export_document
from .sharepoint import SharePointClient, client_from_env


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
        provided, the SharePoint identifiers are read from
        ``SHAREPOINT_SITE_ID`` and ``SHAREPOINT_DRIVE_ID`` environment
        variables and the access token is resolved via the secrets interface.

    Returns
    -------
    str | None
        The item id returned by SharePoint or ``None`` when no upload was
        performed because the CMS is not configured for SharePoint.
    """
    if config.cms.lower() != "sharepoint":
        return None

    if client is None:
        client = client_from_env()

    data, _, filename = export_document(document, fmt, name_template=config.filename_template)
    return client.upload_file(filename, data)
