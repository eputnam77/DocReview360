import pytest

import docreview360.integrations.registry as registry


def test_providers_returns_copy(monkeypatch):
    monkeypatch.setattr(registry, "_providers", {})

    class Dummy:
        pass

    registry.register_provider(Dummy, name="x")
    snapshot = registry.providers()
    snapshot.pop("x")

    # The original registry should remain intact despite modifications
    # to the returned dictionary.
    assert "x" in registry.provider_names()


def test_register_provider_blank_name(monkeypatch) -> None:
    monkeypatch.setattr(registry, "_providers", {})

    class Dummy:
        pass

    with pytest.raises(ValueError):
        registry.register_provider(Dummy, name="")
