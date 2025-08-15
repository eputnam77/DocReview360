from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from threading import Lock
from typing import Callable, Dict, Optional


class SecretVault:
    """Simple in-memory secret store with rotation support."""

    def __init__(self) -> None:
        self._secrets: Dict[str, tuple[str, datetime]] = {}
        self._lock = Lock()

    def store(self, provider: str, secret: str, *, ttl: timedelta | None = None) -> None:
        """Store ``secret`` for ``provider`` with optional ``ttl``."""
        expiry = datetime.utcnow() + (ttl or timedelta(days=90))
        with self._lock:
            self._secrets[provider] = (secret, expiry)

    def get(self, provider: str) -> Optional[str]:
        """Return the secret for ``provider`` if present and not expired."""
        with self._lock:
            item = self._secrets.get(provider)
        if not item:
            return None
        secret, expiry = item
        if datetime.utcnow() >= expiry:
            raise RuntimeError("secret expired")
        return secret

    async def rotate(self, provider: str, loader: Callable[[], str], interval: timedelta) -> None:
        """Periodically rotate ``provider`` secret using ``loader`` every ``interval``."""
        while True:
            await asyncio.sleep(interval.total_seconds())
            self.store(provider, loader(), ttl=interval)


_vault = SecretVault()


def get_secret(provider: str) -> Optional[str]:
    """Return the secret for ``provider`` if available."""
    return _vault.get(provider)


def store_secret(provider: str, secret: str, *, ttl: timedelta | None = None) -> None:
    """Store ``secret`` for ``provider`` with optional ``ttl``."""
    _vault.store(provider, secret, ttl=ttl)


def schedule_rotation(provider: str, loader: Callable[[], str], interval: timedelta) -> None:
    """Schedule automatic rotation of ``provider`` secret."""
    asyncio.create_task(_vault.rotate(provider, loader, interval))

