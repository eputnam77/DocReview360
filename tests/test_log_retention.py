import hashlib
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import insert

from docreview360.celery_app import app
from docreview360.logs import (
    _get_db,
    log_event,
    logs,
    purge_expired_logs,
    schedule_log_purge,
)
from docreview360.models import AuditLog


def test_purge_expired_logs() -> None:
    logs.clear()
    db = _get_db()
    old_ts = datetime.now(timezone.utc) - timedelta(days=400)
    payload = {
        "id": "old",
        "timestamp": old_ts.isoformat(),
        "user_id": "u",
        "action": "old",
        "entity_type": None,
        "entity_id": None,
        "details": {},
        "severity": "info",
        "ip_address": None,
        "prev_hash": None,
        "document_hash": None,
        "provider_response": {},
    }
    encoded = json.dumps(payload, sort_keys=True, default=str).encode()
    payload_db = payload | {"hash": hashlib.sha256(encoded).hexdigest(), "timestamp": old_ts}
    with db.session() as conn:
        conn = conn.execution_options(allow_audit_log_mutations=True)
        conn.execute(insert(AuditLog).values(**payload_db))
    log_event("new")
    removed = purge_expired_logs(365)
    assert removed == 1
    actions = [row.action for row in logs]
    assert "old" not in actions


def test_schedule_log_purge() -> None:
    schedule_log_purge()
    entry = app.conf.beat_schedule["purge_expired_logs"]
    assert entry["args"][0] == 365
