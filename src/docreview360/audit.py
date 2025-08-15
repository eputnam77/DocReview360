"""Document audit logging utilities."""

from __future__ import annotations

from dataclasses import field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:  # pragma: no cover - pydantic optional
    from pydantic.dataclasses import dataclass as pydantic_dataclass
except Exception:  # pragma: no cover
    from dataclasses import dataclass as pydantic_dataclass  # type: ignore


@pydantic_dataclass
class AuditEvent:
    """Structured audit log entry for document events.

    The model doubles as the canonical schema for all audit logging
    within DocReview360. ``doc_id`` is optional to allow reuse of this
    schema by generic log events that may not target a specific
    document.
    """

    timestamp: datetime
    event: str
    user: Optional[str] = None
    doc_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    # Backwards compatibility aliases -------------------------------------
    @property
    def action(self) -> str:  # pragma: no cover - trivial accessor
        """Alias of :attr:`event` used by legacy utilities."""

        return self.event

    @property
    def metadata(self) -> Dict[str, Any]:  # pragma: no cover - trivial accessor
        """Alias of :attr:`details` used by legacy utilities."""

        return self.details

    def model_dump(
        self, *args: Any, **kwargs: Any
    ) -> Dict[str, Any]:  # pragma: no cover - simple passthrough
        return {
            "timestamp": self.timestamp,
            "event": self.event,
            "user": self.user,
            "doc_id": self.doc_id,
            "details": self.details,
        }


try:  # pragma: no cover - pydantic optional
    AUDIT_EVENT_SCHEMA: Dict[str, Any] = AuditEvent.__pydantic_model__.model_json_schema()  # type: ignore[attr-defined]
except Exception:  # pragma: no cover
    AUDIT_EVENT_SCHEMA = {
        "type": "object",
        "properties": {
            "timestamp": {"type": "string", "format": "date-time"},
            "event": {"type": "string"},
            "user": {"type": ["string", "null"]},
            "doc_id": {"type": ["string", "null"]},
            "details": {"type": "object"},
        },
        "required": ["timestamp", "event"],
        "additionalProperties": False,
    }


audit_log: Dict[str, List[AuditEvent]] = {}


def log_audit_event(
    doc_id: str, event: str, user: str | None = None, **details: Any
) -> AuditEvent:
    """Record an :class:`AuditEvent` for ``doc_id`` and return it."""

    entry = AuditEvent(
        timestamp=datetime.now(timezone.utc),
        doc_id=doc_id,
        event=event,
        user=user,
        details=details,
    )
    audit_log.setdefault(doc_id, []).append(entry)
    return entry


def get_audit_log(doc_id: str) -> List[AuditEvent]:
    """Return the audit log for ``doc_id``."""

    return list(audit_log.get(doc_id, []))


def clear_audit_log() -> None:
    """Remove all audit events (useful for tests)."""

    audit_log.clear()
