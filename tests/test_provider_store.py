from pathlib import Path

from docreview360 import provider_store


def test_provider_store_priority_and_health(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "providers.yaml"
    monkeypatch.setattr(provider_store, "PROVIDERS_FILE", path)
    monkeypatch.setattr(provider_store, "DEFAULT_PROVIDERS", {})
    providers = {
        "p1": {"api_key": "", "priority": 1, "healthy": True},
        "p2": {"api_key": "", "priority": 5, "healthy": True},
        "p3": {"api_key": "", "priority": 2, "healthy": False},
    }
    provider_store.save_providers(providers, path)
    assert provider_store.get_active_providers(path) == ["p1", "p2"]
    provider_store.set_provider_health("p2", False, path)
    assert provider_store.get_active_providers(path) == ["p1"]
