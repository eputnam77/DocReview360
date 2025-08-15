"""Audit logging primitives."""

from __future__ import annotations

import json
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


class AuditEvent(BaseModel):
    """Structured audit log entry.

    The canonical schema contains four top‑level fields:

    ``timestamp`` – when the event occurred (UTC).
    ``actor`` – who triggered the event, if known.
    ``action`` – description of what happened.
    ``context`` – free‑form key/value metadata providing additional detail.
    """

    timestamp: datetime = Field()
    actor: Optional[str] = None
    action: str
    context: Dict[str, Any] = Field(default_factory=dict)

    # Backwards compatibility aliases -------------------------------------
    @property
    def user(self) -> Optional[str]:  # pragma: no cover - trivial accessor
        return self.actor

    @property
    def event(self) -> str:  # pragma: no cover - trivial accessor
        return self.action

    @property
    def details(self) -> Dict[str, Any]:  # pragma: no cover - trivial accessor
        return self.context

    @property
    def metadata(self) -> Dict[str, Any]:  # pragma: no cover - trivial accessor
        return self.context


AUDIT_EVENT_SCHEMA: Dict[str, Any] = AuditEvent.model_json_schema()


# append-only datastore -----------------------------------------------------

_AUDIT_LOG_PATH = Path(__file__).with_name("audit.log")


def log_audit_event(
    doc_id: str,
    action: str,
    actor: str | None = None,
    *,
    ip_address: str | None = None,
    provider: str | None = None,
    signature_id: str | None = None,
    document_hash: str | None = None,
    **context: Any,
) -> AuditEvent:
    """Record an :class:`AuditEvent` for ``doc_id`` and return it."""

    entry = AuditEvent(
        timestamp=datetime.now(timezone.utc),
        action=action,
        actor=actor,
        context={
            "doc_id": doc_id,
            "ip_address": ip_address,
            "provider": provider,
            "signature_id": signature_id,
            "document_hash": document_hash,
            **context,
        },
    )

    data = entry.model_dump()
    data["timestamp"] = entry.timestamp.isoformat()
    _AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _AUDIT_LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(data) + "\n")
    return entry


def get_audit_log(doc_id: str) -> List[AuditEvent]:
    """Return the audit log for ``doc_id``."""

    events: List[AuditEvent] = []
    if not _AUDIT_LOG_PATH.exists():
        return events
    with _AUDIT_LOG_PATH.open("r", encoding="utf-8") as fh:
        for line in fh:
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if data.get("context", {}).get("doc_id") != doc_id:
                continue
            try:
                data["timestamp"] = datetime.fromisoformat(data["timestamp"])
                events.append(AuditEvent(**data))
            except Exception:
                continue
    return events


def clear_audit_log() -> None:
    """Remove all audit events (useful for tests)."""

    if _AUDIT_LOG_PATH.exists():
        _AUDIT_LOG_PATH.unlink()
