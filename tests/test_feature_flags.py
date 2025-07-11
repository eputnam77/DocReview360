import pytest

from docreview360 import feature_flags


class DummyClient:
    def __init__(self, url: str, app_name: str, custom_headers: dict):
        self.flags: set[str] = set()

    def initialize_client(self) -> None:
        pass

    def is_enabled(self, name: str, context: dict | None = None) -> bool:
        return name in self.flags


def test_feature_flag_enabled(monkeypatch) -> None:
    calls: list[int] = []
    monkeypatch.setattr(feature_flags, "UnleashClient", DummyClient)
    monkeypatch.setattr(feature_flags, "record_task_completion", lambda x: calls.append(x))

    ff = feature_flags.FeatureFlags("u", "k")
    ff.client.flags.add("flag1")
    assert ff.is_enabled("flag1") is True
    assert ff.is_enabled("flag2") is False
    assert calls == [139]


def test_feature_flags_missing(monkeypatch) -> None:
    monkeypatch.setattr(feature_flags, "UnleashClient", None)
    with pytest.raises(RuntimeError):
        feature_flags.FeatureFlags("u", "k")
