"""CMS persistence helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional
from typing import Protocol

from .object_storage import download_file, upload_file
from .settings_manager import load_settings

from .config import Config
from .documents import DocumentModel
from .exporter import export_document
from .sharepoint import SharePointClient, client_from_env


class CMSBackend(Protocol):
    """Minimal interface for CMS clients."""

    name: str

    def upload(self, filename: str, data: bytes) -> str:
        """Upload document bytes to the CMS."""

    def download(self, item_id: str) -> bytes:
        """Download document bytes from the CMS."""


@dataclass(frozen=True)
class SharePointBackend:
    """SharePoint-backed CMS client."""

    client: SharePointClient
    name: str = "sharepoint"

    def upload(self, filename: str, data: bytes) -> str:
        return self.client.upload_file(filename, data)

    def download(self, item_id: str) -> bytes:
        return self.client.download_file(item_id)


@dataclass(frozen=True)
class FileCMSBackend:
    """File-based CMS backend for local, Confluence, or Google Drive."""

    name: str
    bucket: str

    def upload(self, filename: str, data: bytes) -> str:
        upload_file(self.bucket, filename, data)
        return filename

    def download(self, item_id: str) -> bytes:
        return download_file(self.bucket, item_id)


DEFAULT_CMS_BUCKETS = {
    "local": "cms_store/local",
    "confluence": "cms_store/confluence",
    "gdrive": "cms_store/gdrive",
}


def _resolve_cms_bucket(name: str) -> str:
    settings = load_settings()
    cms_settings = settings.get("cms", {}) if isinstance(settings, dict) else {}
    bucket: str | None = None
    if isinstance(cms_settings, dict):
        backend_settings = cms_settings.get(name)
        if isinstance(backend_settings, dict):
            bucket = backend_settings.get("bucket")
        elif isinstance(backend_settings, str):
            bucket = backend_settings
    if not bucket:
        bucket = os.getenv(f"DOCREVIEW360_{name.upper()}_CMS_BUCKET")
    return bucket or DEFAULT_CMS_BUCKETS[name]


def _cms_name(config: Config) -> str:
    return config.cms.strip().lower()


def get_cms_backend(
    *,
    config: Config,
    client: Optional[SharePointClient] = None,
) -> CMSBackend | None:
    """Return a CMS backend instance for the configured CMS."""

    name = _cms_name(config)
    if not name or name == "none":
        return None
    if name == "sharepoint":
        return SharePointBackend(client or client_from_env())
    if name in DEFAULT_CMS_BUCKETS:
        return FileCMSBackend(name=name, bucket=_resolve_cms_bucket(name))
    raise ValueError(f"Unsupported CMS backend: {name}")


def save_to_cms(
    document: DocumentModel,
    *,
    config: Config,
    fmt: str = "markdown",
    client: Optional[SharePointClient] = None,
) -> str | None:
    """Persist ``document`` to the configured CMS.

    The document is exported using :func:`export_document` and uploaded to the
    configured CMS backend. The generated filename honours the
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
        The item id returned by the CMS or ``None`` when no upload was
        performed because the CMS is disabled.
    """
    backend = get_cms_backend(config=config, client=client)
    if backend is None:
        return None
    data, _, filename = export_document(document, fmt, name_template=config.filename_template)
    return backend.upload(filename, data)


def fetch_from_cms(
    item_id: str,
    *,
    config: Config,
    client: Optional[SharePointClient] = None,
) -> bytes | None:
    """Fetch document bytes from the configured CMS."""

    backend = get_cms_backend(config=config, client=client)
    if backend is None:
        return None
    return backend.download(item_id)
