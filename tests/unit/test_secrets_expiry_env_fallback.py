import types
from datetime import datetime, timedelta, timezone

import pytest

import docreview360.secrets as secrets
from docreview360.secrets import get_secret, store_secret


def test_expired_secret_falls_back_to_env(monkeypatch: pytest.MonkeyPatch) -> None:
    secrets._vault._secrets.clear()
    store_secret("p", "value", ttl=timedelta(seconds=1))

    # Advance time beyond the stored secret's expiry.
    future = datetime.now(timezone.utc) + timedelta(seconds=5)
    monkeypatch.setattr(
        secrets,
        "datetime",
        types.SimpleNamespace(now=lambda tz: future),
    )

    # Environment variable should be returned once the secret expires rather
    # than raising an exception.
    monkeypatch.setenv("P_TOKEN", "env-value")
    assert get_secret("p") == "env-value"
