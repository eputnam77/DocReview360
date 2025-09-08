import pytest

from docreview360 import profile


def test_get_preferences_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[str, dict[str, object]] = {}
    monkeypatch.setattr(profile, "load_settings", lambda: store)
    assert profile.get_preferences("alice") == {}


def test_update_preferences_string_bool(monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[str, dict[str, object]] = {}

    def load() -> dict[str, dict[str, object]]:
        return store

    def update(key: str, value: dict[str, object]) -> None:
        store[key] = value

    monkeypatch.setattr(profile, "load_settings", load)
    monkeypatch.setattr(profile, "update_setting", update)
    result = profile.update_preferences("bob", {"reduce_motion": "false"})
    assert result["reduce_motion"] is False
    assert store["prefs_bob"]["reduce_motion"] is False


def test_update_preferences_theme_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[str, dict[str, object]] = {}

    def load() -> dict[str, dict[str, object]]:
        return store

    def update(key: str, value: dict[str, object]) -> None:
        store[key] = value

    monkeypatch.setattr(profile, "load_settings", load)
    monkeypatch.setattr(profile, "update_setting", update)
    result = profile.update_preferences("alice", {"theme": "Dark"})
    assert result["theme"] == "dark"
    assert store["prefs_alice"]["theme"] == "dark"


def test_update_preferences_theme_stripped(monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[str, dict[str, object]] = {}

    def load() -> dict[str, dict[str, object]]:
        return store

    def update(key: str, value: dict[str, object]) -> None:
        store[key] = value

    monkeypatch.setattr(profile, "load_settings", load)
    monkeypatch.setattr(profile, "update_setting", update)
    result = profile.update_preferences("carol", {"theme": " Light "})
    assert result["theme"] == "light"
    assert store["prefs_carol"]["theme"] == "light"


def test_update_preferences_requires_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[str, dict[str, object]] = {}

    def load() -> dict[str, dict[str, object]]:
        return store

    def update(key: str, value: dict[str, object]) -> None:
        store[key] = value

    monkeypatch.setattr(profile, "load_settings", load)
    monkeypatch.setattr(profile, "update_setting", update)

    with pytest.raises(TypeError):
        profile.update_preferences("dave", [("theme", "dark")])
