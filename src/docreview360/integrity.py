# SPDX-License-Identifier: MIT
"""Integrity verification tasks for CMS stored documents."""

from __future__ import annotations

import hashlib
import logging
from typing import List

try:
    from celery.schedules import crontab
except ModuleNotFoundError:  # pragma: no cover - optional worker extra
    crontab = None  # type: ignore[assignment]

from .audit import log_audit_event
from .config import CONFIG_FILE, Config
from .documents import documents
from .logs import log_event

try:
    from .celery_app import app
except ModuleNotFoundError:  # pragma: no cover - optional worker extra
    app = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


def client_from_env():
    """Return the configured SharePoint client without importing it at module load."""

    from .sharepoint import client_from_env as _client_from_env

    return _client_from_env()


def verify_integrity() -> List[str]:
    """Re-hash CMS files and compare against stored ingestion hashes.

    Returns a list of document ids where the CMS copy differs.
    """
    cfg = Config.load(CONFIG_FILE)
    # ``cms`` values may come from configuration files where users sometimes
    # leave stray whitespace. Normalise before comparing so a value like
    # ``"sharepoint "`` still enables the integrity check.
    if not cfg or cfg.cms.strip().lower() != "sharepoint":
        return []
    try:
        client = client_from_env()
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


if app is not None:
    verify_integrity = app.task(name="docreview360.verify_integrity")(verify_integrity)


def schedule_integrity_check() -> None:
    """Schedule the periodic integrity verification task."""
    if app is None or crontab is None:
        logger.warning(
            "Integrity scheduling requires an optional install. "
            "Run: pip install \"docreview360[worker]\""
        )
        return
    app.conf.beat_schedule = app.conf.get("beat_schedule", {})
    app.conf.beat_schedule["integrity_check"] = {
        "task": "docreview360.verify_integrity",
        "schedule": crontab(hour=3, minute=0),
    }
