from __future__ import annotations

from datetime import timedelta
from typing import Dict

from docreview360.celery_app import app
from docreview360.integrations.signature import get_provider
from docreview360.monitoring import PROVIDER_HEALTH
from docreview360.provider_store import load_providers, set_provider_health


def check_provider_health() -> Dict[str, bool]:
    """Ping configured providers and update health metrics."""

    results: Dict[str, bool] = {}
    providers = load_providers()
    for name in providers:
        try:
            provider = get_provider(name)
            healthy = bool(getattr(provider, "health_check", lambda: True)())
        except Exception:  # pragma: no cover - provider lookup or call failed
            healthy = False
        set_provider_health(name, healthy)
        PROVIDER_HEALTH.labels(name).set(1 if healthy else 0)
        results[name] = healthy
    return results


check_provider_health_task = app.task(name="docreview360.check_provider_health")(check_provider_health)


def schedule_provider_health_checks(interval_minutes: int = 5) -> None:
    """Schedule periodic provider health checks."""
    if interval_minutes <= 0:
        raise ValueError("interval_minutes must be positive")

    app.conf.beat_schedule = app.conf.get("beat_schedule", {})
    app.conf.beat_schedule["provider_health"] = {
        "task": "docreview360.check_provider_health",
        "schedule": timedelta(minutes=interval_minutes),
    }
