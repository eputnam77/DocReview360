"""Feature flag utilities."""

from __future__ import annotations

from typing import Any

try:
    from UnleashClient import UnleashClient
except Exception:  # pragma: no cover - optional dep
    UnleashClient = None

from .stubs import record_task_completion


class FeatureFlags:
    """Wrapper around UnleashClient."""

    def __init__(self, url: str, api_key: str) -> None:
        if UnleashClient is None:
            raise RuntimeError("UnleashClient not installed")
        self.client = UnleashClient(
            url=url, app_name="docuflow", custom_headers={"Authorization": api_key}
        )
        self.client.initialize_client()

    def is_enabled(self, name: str, context: dict[str, Any] | None = None) -> bool:
        """Return True if ``name`` flag is enabled."""
        result = self.client.is_enabled(name, context or {})
        record_task_completion(139)
        return bool(result)
