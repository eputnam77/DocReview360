"""Document audit logging utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:  # pragma: no cover - pydantic optional
    from pydantic.dataclasses import dataclass as pydantic_dataclass
except Exception:  # pragma: no cover
    from dataclasses import dataclass as pydantic_dataclass  # type: ignore


@pydantic_dataclass
class AuditEvent:
    """Structured audit log entry for document events."""

    timestamp: datetime
    doc_id: str
    event: str
    user: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def model_dump(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:  # pragma: no cover - simple passthrough
        return {
            "timestamp": self.timestamp,
            "doc_id": self.doc_id,
            "event": self.event,
            "user": self.user,
            "details": self.details,
        }


audit_log: Dict[str, List[AuditEvent]] = {}


def log_audit_event(doc_id: str, event: str, user: str | None = None, **details: Any) -> AuditEvent:
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
