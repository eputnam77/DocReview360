"""Integrity verification tasks for CMS stored documents."""

from __future__ import annotations

import hashlib
import logging
import os
from typing import List

from celery.schedules import crontab

from .audit import log_audit_event
from .celery_app import app
from .config import CONFIG_FILE, Config
from .documents import documents
from .logs import log_event
from .sharepoint import SharePointClient

logger = logging.getLogger(__name__)


def _client_from_env() -> SharePointClient:
    """Return a SharePoint client using environment credentials."""
    site_id = os.getenv("SHAREPOINT_SITE_ID")
    drive_id = os.getenv("SHAREPOINT_DRIVE_ID")
    token = os.getenv("SHAREPOINT_TOKEN")
    if not all([site_id, drive_id, token]):
        raise ValueError("Missing SharePoint credentials")
    return SharePointClient(site_id=site_id, drive_id=drive_id, token=token)


def verify_integrity() -> List[str]:
    """Re-hash CMS files and compare against stored ingestion hashes.

    Returns a list of document ids where the CMS copy differs.
    """
    cfg = Config.load(CONFIG_FILE)
    if not cfg or cfg.cms.lower() != "sharepoint":
        return []
    try:
        client = _client_from_env()
    except Exception as exc:  # pragma: no cover - environment dependent
        logger.error("Integrity check skipped: %s", exc)
        return []

    mismatches: List[str] = []
    for doc in documents.values():
        if not doc.ingestion_hash:
            continue
        try:
            data = client.download_file(doc.id)
        except Exception as exc:  # pragma: no cover - network errors
            logger.error("Failed to fetch %s: %s", doc.id, exc)
            continue
        digest = hashlib.sha256(data).hexdigest()
        if digest != doc.ingestion_hash:
            logger.warning("Ingestion hash mismatch for %s", doc.id)
            log_event(
                "integrity_mismatch",
                document=doc.id,
                expected=doc.ingestion_hash,
                actual=digest,
            )
            log_audit_event(
                doc.id,
                "integrity_mismatch",
                expected=doc.ingestion_hash,
                actual=digest,
            )
            mismatches.append(doc.id)
    return mismatches


verify_integrity = app.task(name="docreview360.verify_integrity")(verify_integrity)


def schedule_integrity_check() -> None:
    """Schedule the periodic integrity verification task."""
    app.conf.beat_schedule = app.conf.get("beat_schedule", {})
    app.conf.beat_schedule["integrity_check"] = {
        "task": "docreview360.verify_integrity",
        "schedule": crontab(hour=3, minute=0),
    }
