"""Audit logging primitives."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:  # pragma: no cover - pydantic optional
    from pydantic import BaseModel, Field
except Exception:  # pragma: no cover

    class BaseModel:  # type: ignore[no-redef]
        """Fallback stub when Pydantic is unavailable."""

        def __init__(self, **data: Any) -> None:  # pragma: no cover - simple shim
            for k, v in data.items():
                setattr(self, k, v)

        def model_dump(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:  # pragma: no cover
            return self.__dict__

        @classmethod
        def model_json_schema(cls) -> Dict[str, Any]:  # pragma: no cover
            return {}


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

    if verified_at is None:
        verified_at = datetime.now(timezone.utc)
    if verifier is None and actor is not None:
        verifier = actor
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
        fh.write(json.dumps(data) + "\n")
    return entry


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
                continue
            if data.get("document_id") != document_id:
                continue
            try:
                expected = _compute_hash({k: v for k, v in data.items() if k != "hash"}, secret)
                if secret and not hmac.compare_digest(expected, data.get("hash", "")):
                    continue
                data["verified_at"] = datetime.fromisoformat(data["verified_at"])
                events.append(AuditLogEntry(**data))
            except Exception:
                continue
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
                continue
            if data.get("id") != entry_id:
                continue
            try:
                expected = _compute_hash({k: v for k, v in data.items() if k != "hash"}, secret)
                if secret and not hmac.compare_digest(expected, data.get("hash", "")):
                    return None
                data["verified_at"] = datetime.fromisoformat(data["verified_at"])
                return AuditLogEntry(**data)
            except Exception:
                return None
    return None


def clear_audit_log() -> None:
    """Remove all audit events (useful for tests)."""

    if _AUDIT_LOG_PATH.exists():
        _AUDIT_LOG_PATH.unlink()
