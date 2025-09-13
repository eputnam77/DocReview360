from __future__ import annotations

import asyncio
import os
import re
from datetime import datetime, timedelta
from threading import Lock
from typing import Callable, Dict, Optional


class VaultClient:
    """Very small in-memory vault with environment fallback."""

    def __init__(self) -> None:
        self._secrets: Dict[str, tuple[str, datetime]] = {}
        self._lock = Lock()
        self.url: str | None = None
        self.token: str | None = None

    def configure(self, *, url: str | None = None, token: str | None = None) -> None:
        """Configure connection details for an external vault."""
        self.url = url
        self.token = token

    def store(self, provider: str, secret: str, *, ttl: timedelta | None = None) -> None:
        """Store ``secret`` for ``provider`` with optional ``ttl``."""
        if not isinstance(provider, str):
            raise TypeError("provider must be a string")
        provider = provider.strip()
        if not provider:
            raise ValueError("provider must be non-empty")
        if not isinstance(secret, str):
            raise TypeError("secret must be a string")
        if ttl is not None and ttl.total_seconds() <= 0:
            raise ValueError("ttl must be positive")
        expiry = datetime.utcnow() + (ttl or timedelta(days=90))
        with self._lock:
            self._secrets[provider] = (secret, expiry)

    def get(self, provider: str) -> Optional[str]:
        """Return the secret for ``provider`` if present or via env vars."""
        if not isinstance(provider, str):
            raise TypeError("provider must be a string")
        provider = provider.strip()
        if not provider:
            raise ValueError("provider must be non-empty")
        with self._lock:
            item = self._secrets.get(provider)
            if item:
                secret, expiry = item
                # Expired secrets should not linger in the in-memory store.
                # Previously they remained even after an expiry check failed
                # which caused every subsequent lookup to raise ``RuntimeError``
                # and prevented falling back to environment variables.  Remove
                # the stale entry so callers can retry or rely on env vars.
                if datetime.utcnow() >= expiry:
                    # Secret expired – remove and fall through to env vars
                    # instead of raising which previously prevented callers
                    # from transparently using configured fallbacks.
                    self._secrets.pop(provider, None)
                else:
                    return secret
        # Fallback to environment variables using common suffixes.  Provider
        # identifiers may include characters not valid in environment variable
        # names such as hyphens.  Normalize to uppercase underscores so a
        # provider like ``"my-service"`` correctly maps to ``MY_SERVICE``
        # based variables.
        base = re.sub(r"[^A-Z0-9]", "_", provider.upper())
        for suffix in ("", "_TOKEN", "_KEY", "_SECRET"):
            value = os.getenv(f"{base}{suffix}")
            if value:
                return value
        return None

    async def rotate(self, provider: str, loader: Callable[[], str], interval: timedelta) -> None:
        """Periodically rotate ``provider`` secret using ``loader`` every ``interval``."""
        while True:
            await asyncio.sleep(interval.total_seconds())
            self.store(provider, loader(), ttl=interval)


_vault = VaultClient()


def get_secret(provider: str) -> Optional[str]:
    """Return the secret for ``provider`` if available."""
    return _vault.get(provider)


def store_secret(provider: str, secret: str, *, ttl: timedelta | None = None) -> None:
    """Store ``secret`` for ``provider`` with optional ``ttl``."""
    _vault.store(provider, secret, ttl=ttl)


def schedule_rotation(
    provider: str, loader: Callable[[], str], interval: timedelta
) -> asyncio.Task[None]:
    """Schedule automatic rotation of ``provider`` secret and return the task.

    Returning the created :class:`asyncio.Task` allows callers (and tests) to
    manage the background coroutine if needed, such as cancelling it during
    shutdown. Previously the task handle was lost, which also made it difficult
    to prevent 'coroutine was never awaited' warnings when `asyncio.create_task`
    was monkeypatched.
    """
    return asyncio.create_task(_vault.rotate(provider, loader, interval))


def configure_vault(config: Dict[str, str]) -> None:
    """Configure the global vault client from settings."""
    _vault.configure(url=config.get("url"), token=config.get("token"))
