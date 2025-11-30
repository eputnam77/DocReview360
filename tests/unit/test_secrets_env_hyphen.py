import pytest

import docreview360.secrets as secrets
from docreview360.secrets import get_secret


def test_env_fallback_normalizes_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    secrets._vault._secrets.clear()
    # Environment variables cannot contain hyphens; the provider name should be
    # normalized to use underscores when performing the lookup.
    monkeypatch.setenv("MY_SERVICE_TOKEN", "env-value")
    assert get_secret("my-service") == "env-value"
