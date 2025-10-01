"""Audit logging primitives."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .object_storage import upload_file
from .security_compliance import should_purge
from .settings_manager import load_settings

logger = logging.getLogger(__name__)


class AuditLogIntegrityError(RuntimeError):
    """Raised when a persisted audit log entry fails validation."""

    def __init__(
        self,
        message: str,
        *,
        reason: str,
        document_id: str | None = None,
        entry_id: str | None = None,
        raw_entry: str | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.document_id = document_id
        self.entry_id = entry_id
        self.raw_entry = raw_entry


class AuditLogEntry(BaseModel):
    """Structured, optionally signed audit log entry."""

    id: str
    event: str
    document_id: str
    approval_id: Optional[str] = None
    status: str = Field(default="unknown")
    hash: str = Field(description="SHA256 or HMAC signature of the entry")
    certificate_url: Optional[str] = None
    verified_at: datetime = Field()
    verifier: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)

    # Backwards compatibility aliases -------------------------------------
    @property
    def action(self) -> str:  # pragma: no cover - trivial accessor
        return self.event

    @property
    def doc_id(self) -> str:  # pragma: no cover - trivial accessor
        return self.document_id

    @property
    def actor(self) -> Optional[str]:  # pragma: no cover - trivial accessor
        return self.verifier

    @property
    def timestamp(self) -> datetime:  # pragma: no cover - trivial accessor
        return self.verified_at

    @property
    def metadata(self) -> Dict[str, Any]:  # pragma: no cover - trivial accessor
        return self.context

    @property
    def details(self) -> Dict[str, Any]:  # pragma: no cover - trivial accessor
        return self.context


AUDIT_LOG_SCHEMA: Dict[str, Any] = AuditLogEntry.model_json_schema()


# append-only datastore -----------------------------------------------------

_AUDIT_LOG_PATH = Path(__file__).with_name("audit.log")
_AUDIT_ANCHOR_PATH = _AUDIT_LOG_PATH.with_suffix(".anchor")

DEFAULT_AUDIT_LOG_SETTINGS: Dict[str, int] = {
    "retention_days": 365 * 7,
    "purge_interval_minutes": 60 * 24,
}


def _compute_hash(data: Dict[str, Any], secret: str | None) -> str:
    payload = json.dumps(data, sort_keys=True, default=str).encode()
    if secret:
        return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hashlib.sha256(payload).hexdigest()


def log_audit_event(
    document_id: str,
    event: str,
    actor: str | None = None,
    *,
    approval_id: str | None = None,
    status: str | None = None,
    certificate_url: str | None = None,
    verifier: str | None = None,
    verified_at: datetime | None = None,
    secret: str | None = None,
    **context: Any,
) -> AuditLogEntry:
    """Record an :class:`AuditLogEntry` for ``document_id`` and return it."""

    from .logs import TRACE_ID  # local import to avoid circular import during module load

    if verified_at is None:
        verified_at = datetime.now(timezone.utc)
    if verifier is None and actor is not None:
        verifier = actor
    trace = context.pop("trace_id", None) or TRACE_ID.get(None)
    if trace:
        context.setdefault("trace_id", trace)
    entry = AuditLogEntry(
        id=str(uuid.uuid4()),
        event=event,
        document_id=document_id,
        approval_id=approval_id or context.pop("approval_id", None),
        status=status or context.pop("status", "unknown"),
        certificate_url=certificate_url or context.pop("certificate_url", None),
        verified_at=verified_at,
        verifier=verifier,
        hash="",
        context=context,
    )
    data = entry.model_dump()
    data_without_hash = {k: v for k, v in data.items() if k != "hash"}
    entry.hash = _compute_hash(data_without_hash, secret)
    data["hash"] = entry.hash
    data["verified_at"] = entry.verified_at.isoformat()
    _AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _AUDIT_LOG_PATH.open("a", encoding="utf-8") as fh:
        # ``_compute_hash`` serialises using ``default=str`` so it gracefully
        # handles non-JSON-native types like ``datetime`` in the ``context``.
        # When persisting the entry we previously called ``json.dumps`` without
        # this option which meant the log function succeeded in computing the
        # hash but then crashed trying to write the event if the context
        # contained such objects.  Use the same ``default=str`` behaviour so the
        # log remains writable for any data that can be hashed above.
        fh.write(json.dumps(data, default=str) + "\n")
    return entry


def _load_audit_log_settings() -> Dict[str, int]:
    settings = load_settings()
    cfg = settings.get("audit_log", {})
    data = DEFAULT_AUDIT_LOG_SETTINGS.copy()
    if isinstance(cfg, dict):
        for key, value in cfg.items():
            if key not in data:
                continue
            try:
                data[key] = int(value)
            except (TypeError, ValueError):
                logger.warning("Ignoring non-integer audit log setting '%s'", key)
    return data


def _dispatch_verification_tasks() -> None:
    try:
        from .integrity import verify_integrity
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Unable to import integrity task: %s", exc)
    else:
        try:
            verify_integrity.delay()
        except AttributeError:
            try:
                verify_integrity()
            except Exception as call_exc:  # pragma: no cover - integrity runtime failure
                logger.warning("Integrity verification call failed: %s", call_exc)
        except Exception as exc:  # pragma: no cover - Celery transport specific
            logger.warning("Failed to enqueue verify_integrity task: %s", exc)

    try:
        hash_new_log_segments()
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to hash new audit log segments: %s", exc)


def _raise_corruption(
    *,
    reason: str,
    message: str,
    document_id: str | None,
    entry_id: str | None,
    raw_entry: str | None,
) -> None:
    context: Dict[str, Any] = {
        "reason": reason,
    }
    if document_id:
        context["document"] = document_id
    if entry_id:
        context["entry_id"] = entry_id

    try:
        from .logs import log_event as _log_event
    except Exception:  # pragma: no cover - defensive lazy import
        logger.exception("Unable to import log_event for corruption alert")
    else:
        try:
            _log_event(
                "audit_log_corruption_detected",
                severity="error",
                **context,
            )
        except Exception:  # pragma: no cover - logging backend failures
            logger.exception("Failed to emit audit_log_corruption_detected event")

    _dispatch_verification_tasks()
    raise AuditLogIntegrityError(
        message,
        reason=reason,
        document_id=document_id,
        entry_id=entry_id,
        raw_entry=raw_entry,
    )


def get_audit_log(document_id: str, secret: str | None = None) -> List[AuditLogEntry]:
    """Return the audit log for ``document_id`` sorted by timestamp."""

    events: List[AuditLogEntry] = []
    if not _AUDIT_LOG_PATH.exists():
        return events
    with _AUDIT_LOG_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                _raise_corruption(
                    reason="malformed_json",
                    message="Encountered malformed audit log entry",
                    document_id=document_id,
                    entry_id=None,
                    raw_entry=line.strip(),
                )
            if data.get("document_id") != document_id:
                continue
            try:
                expected = _compute_hash({k: v for k, v in data.items() if k != "hash"}, secret)
                if secret and not hmac.compare_digest(expected, data.get("hash", "")):
                    _raise_corruption(
                        reason="hash_mismatch",
                        message="Audit log entry failed HMAC verification",
                        document_id=document_id,
                        entry_id=str(data.get("id")),
                        raw_entry=json.dumps(data, default=str),
                    )
                data["verified_at"] = datetime.fromisoformat(data["verified_at"])
                events.append(AuditLogEntry(**data))
            except AuditLogIntegrityError:
                raise
            except Exception as exc:
                _raise_corruption(
                    reason="unreadable_entry",
                    message=f"Failed to hydrate audit log entry: {exc}",
                    document_id=document_id,
                    entry_id=str(data.get("id")),
                    raw_entry=json.dumps(data, default=str),
                )
    events.sort(key=lambda e: e.verified_at)
    return events


def get_audit_entry(entry_id: str, secret: str | None = None) -> AuditLogEntry | None:
    """Return a single audit log entry by ``entry_id`` if present."""

    if not _AUDIT_LOG_PATH.exists():
        return None
    with _AUDIT_LOG_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                _raise_corruption(
                    reason="malformed_json",
                    message="Encountered malformed audit log entry",
                    document_id=None,
                    entry_id=entry_id,
                    raw_entry=line.strip(),
                )
            if data.get("id") != entry_id:
                continue
            try:
                expected = _compute_hash({k: v for k, v in data.items() if k != "hash"}, secret)
                if secret and not hmac.compare_digest(expected, data.get("hash", "")):
                    _raise_corruption(
                        reason="hash_mismatch",
                        message="Audit log entry failed HMAC verification",
                        document_id=str(data.get("document_id")),
                        entry_id=entry_id,
                        raw_entry=json.dumps(data, default=str),
                    )
                data["verified_at"] = datetime.fromisoformat(data["verified_at"])
                return AuditLogEntry(**data)
            except AuditLogIntegrityError:
                raise
            except Exception as exc:
                _raise_corruption(
                    reason="unreadable_entry",
                    message=f"Failed to hydrate audit log entry: {exc}",
                    document_id=str(data.get("document_id")),
                    entry_id=entry_id,
                    raw_entry=json.dumps(data, default=str),
                )
    return None


def clear_audit_log() -> None:
    """Remove all audit events (useful for tests)."""

    if _AUDIT_LOG_PATH.exists():
        _AUDIT_LOG_PATH.unlink()


def purge_audit_logs(retention_days: int | None = None) -> int:
    """Remove audit log entries older than ``retention_days``.

    Returns
    -------
    int
        Number of entries removed.
    """

    if retention_days is None:
        retention_days = _load_audit_log_settings()["retention_days"]

    if not _AUDIT_LOG_PATH.exists():
        return 0
    removed = 0
    keep: List[str] = []
    with _AUDIT_LOG_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            try:
                data = json.loads(line)
                created = datetime.fromisoformat(data["verified_at"])
                if should_purge(created, retention_days):
                    removed += 1
                    continue
            except Exception:
                pass
            keep.append(line)
    if removed:
        if keep:
            with _AUDIT_LOG_PATH.open("w", encoding="utf-8") as fh:
                for line in keep:
                    fh.write(line)
        else:
            _AUDIT_LOG_PATH.unlink()
    return removed


def hash_new_log_segments(
    *,
    bucket: str | Path = "tamper_proof_store",
    prefix: str = "audit_anchors",
    segment_size: int = 100,
    retention_days: int = 365,
) -> int:
    """Hash new audit log segments and store digests in append-only storage.

    Parameters
    ----------
    bucket:
        Directory or S3 bucket where segment hashes are stored.
    prefix:
        Subdirectory or key prefix for stored hashes.
    segment_size:
        Number of log entries per segment.
    retention_days:
        Retention period applied when storing hashes with object lock.

    Returns
    -------
    int
        Number of segments hashed during this invocation.
    """
    if segment_size <= 0:
        raise ValueError("segment_size must be positive")
    if retention_days < 0:
        raise ValueError("retention_days must be non-negative")

    if not _AUDIT_LOG_PATH.exists():
        return 0

    start = 0
    if _AUDIT_ANCHOR_PATH.exists():
        try:
            start = int(_AUDIT_ANCHOR_PATH.read_text())
        except Exception:
            start = 0
    # ``start`` is stored on disk and may become negative if a previous run
    # crashed mid-write or the file was tampered with.  Python slices treat
    # negative indices as offsets from the end which would skip earlier log
    # entries and corrupt the audit trail.  Clamp to zero so we always
    # process from the beginning when encountering a corrupt anchor value.
    if start < 0:
        start = 0

    with _AUDIT_LOG_PATH.open("r", encoding="utf-8") as fh:
        lines = fh.readlines()

    total_lines = len(lines)
    if start > total_lines:
        start = total_lines

    new_lines = lines[start:]
    if not new_lines:
        _AUDIT_ANCHOR_PATH.write_text(str(total_lines))
        return 0

    count = 0
    for i in range(0, len(new_lines), segment_size):
        segment = new_lines[i : i + segment_size]
        digest = hashlib.sha256("".join(segment).encode("utf-8")).hexdigest()
        index = (start // segment_size) + count
        key = f"{prefix}/segment_{index}.sha256"
        upload_file(bucket, key, digest.encode(), append_only=True, retention_days=retention_days)
        count += 1

    _AUDIT_ANCHOR_PATH.write_text(str(start + len(new_lines)))
    return count


def schedule_audit_log_purge() -> None:
    """Configure periodic purging of expired audit log entries."""
    from .celery_app import app

    cfg = _load_audit_log_settings()
    retention = cfg["retention_days"]
    interval = cfg.get(
        "purge_interval_minutes", DEFAULT_AUDIT_LOG_SETTINGS["purge_interval_minutes"]
    )
    app.task(name="docreview360.purge_audit_logs")(purge_audit_logs)
    app.conf.beat_schedule = app.conf.get("beat_schedule", {})
    app.conf.beat_schedule["purge_audit_logs"] = {
        "task": "docreview360.purge_audit_logs",
        "schedule": timedelta(minutes=interval),
        "args": (retention,),
    }


def schedule_audit_log_hashing() -> None:
    """Configure periodic hashing of new audit log segments."""
    from .celery_app import app

    settings = load_settings()
    cfg = settings.get("audit_log", {})
    interval = int(cfg.get("hash_interval_minutes", 60))
    bucket = str(cfg.get("hash_bucket", "tamper_proof_store"))
    prefix = str(cfg.get("hash_prefix", "audit_anchors"))
    segment_size = int(cfg.get("hash_segment_size", 100))
    retention = int(cfg.get("hash_retention_days", 365))
    app.task(name="docreview360.hash_new_log_segments")(hash_new_log_segments)
    app.conf.beat_schedule = app.conf.get("beat_schedule", {})
    app.conf.beat_schedule["hash_audit_log"] = {
        "task": "docreview360.hash_new_log_segments",
        "schedule": timedelta(minutes=interval),
        "kwargs": {
            "bucket": bucket,
            "prefix": prefix,
            "segment_size": segment_size,
            "retention_days": retention,
        },
    }
