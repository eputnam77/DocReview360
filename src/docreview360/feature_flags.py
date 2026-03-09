"""Feature flag utilities."""

from __future__ import annotations

from typing import Any

try:
    from UnleashClient import UnleashClient
except Exception:
    UnleashClient = None


def record_task_completion(item: int) -> None:  # pragma: no cover
    """Record completion of a release checklist item (no-op stub)."""


class FeatureFlags:
    """Wrapper around UnleashClient."""

    def __init__(self, url: str, api_key: str) -> None:
        if UnleashClient is None:
            raise RuntimeError("UnleashClient not installed")
        self.client = UnleashClient(
            url=url, app_name="docreview360", custom_headers={"Authorization": api_key}
        )
        self.client.initialize_client()
        self._logged = False

    def is_enabled(self, name: str, context: dict[str, Any] | None = None) -> bool:
        """Return True if ``name`` flag is enabled."""
        result = self.client.is_enabled(name, context or {})
        if not self._logged:
            self._logged = True
            record_task_completion(139)
        return bool(result)
