from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from docreview360.celery_app import app
from docreview360.log_hash_chain import verify_hash_chain
from docreview360.logs import log_event
from docreview360.monitoring import VERIFICATION_COUNTER, VERIFICATION_DURATION
from docreview360.settings_manager import load_settings


def verify_log_chain(
    bucket: str | Path = "tamper_proof_store",
    key: str = "log_chain.json",
    batch_size: int = 100,
    *,
    user_id: str = "system",
    alert_email: str | None = None,
) -> bool:
    """Recompute hash chain and log the verification result.

    Parameters
    ----------
    bucket:
        Directory or object storage bucket containing the persisted hash chain.
    key:
        File name of the stored chain within ``bucket``.
    batch_size:
        Number of log entries per batch used when recomputing the chain.

    Returns
    -------
    bool
        ``True`` when the current logs match the stored chain, ``False`` otherwise.
    """
    with VERIFICATION_DURATION.labels("log_chain").time():
        ok = verify_hash_chain(bucket=bucket, key=key, batch_size=batch_size, user_id=user_id)
    log_event(
        "log_chain_verification",
        user_id=user_id,
        result="success" if ok else "mismatch",
    )
    VERIFICATION_COUNTER.labels("log_chain", "success" if ok else "mismatch").inc()
    if not ok:
        log_event("log_chain_integrity_failure", user_id=user_id)
        if alert_email:
            from docreview360.notifications import send_email

            send_email(
                "default",
                alert_email,
                subject="Log chain verification failed",
                body="Stored log hash chain does not match current logs.",
            )
    return ok


# Expose a Celery task separately so calling ``verify_log_chain`` directly does
# not trigger task lifecycle logging, which would otherwise interfere with the
# hash-chain verification performed inside the function.
verify_log_chain_task = app.task(name="docreview360.verify_log_chain")(verify_log_chain)


def schedule_log_chain_verification() -> None:
    """Configure periodic log chain verification based on settings."""
    settings = load_settings()
    cfg = settings.get("log_chain_verification", {})
    interval = int(cfg.get("interval_minutes", 60))
    bucket = str(cfg.get("bucket", "tamper_proof_store"))
    key = str(cfg.get("key", "log_chain.json"))
    batch_size = int(cfg.get("batch_size", 100))
    alert_email = str(cfg.get("alert_email", "admin@example.com"))
    app.conf.beat_schedule = app.conf.get("beat_schedule", {})
    app.conf.beat_schedule["log_chain_verification"] = {
        "task": "docreview360.verify_log_chain",
        "schedule": timedelta(minutes=interval),
        "kwargs": {
            "bucket": bucket,
            "key": key,
            "batch_size": batch_size,
            "alert_email": alert_email,
        },
    }
