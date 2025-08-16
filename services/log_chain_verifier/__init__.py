from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from docreview360.celery_app import app
from docreview360.log_hash_chain import verify_hash_chain
from docreview360.logs import log_event
from docreview360.settings_manager import load_settings


def verify_log_chain(
    bucket: str | Path = "tamper_proof_store",
    key: str = "log_chain.json",
    batch_size: int = 100,
) -> bool:
    """Recompute hash chain and log failures to the audit log.

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
    ok = verify_hash_chain(bucket=bucket, key=key, batch_size=batch_size)
    if not ok:
        log_event("log_chain_integrity_failure")
    return ok


verify_log_chain = app.task(name="docreview360.verify_log_chain")(verify_log_chain)


def schedule_log_chain_verification() -> None:
    """Configure periodic log chain verification based on settings."""
    settings = load_settings()
    cfg = settings.get("log_chain_verification", {})
    interval = int(cfg.get("interval_minutes", 60))
    bucket = str(cfg.get("bucket", "tamper_proof_store"))
    key = str(cfg.get("key", "log_chain.json"))
    batch_size = int(cfg.get("batch_size", 100))
    app.conf.beat_schedule = app.conf.get("beat_schedule", {})
    app.conf.beat_schedule["log_chain_verification"] = {
        "task": "docreview360.verify_log_chain",
        "schedule": timedelta(minutes=interval),
        "kwargs": {"bucket": bucket, "key": key, "batch_size": batch_size},
    }
