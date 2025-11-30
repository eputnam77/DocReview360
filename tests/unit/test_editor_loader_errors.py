import pytest

from docreview360 import editor_loader


def test_load_plugins_rejects_non_callable() -> None:
    with pytest.raises(TypeError):
        list(editor_loader.load_plugins(["not_callable"]))


def test_load_plugins_rejects_empty_name() -> None:
    def loader():
        return ""

    with pytest.raises(ValueError):
        editor_loader.load_plugins([loader])


def test_load_plugins_rejects_non_string_name() -> None:
    def loader():
        return 123  # type: ignore[return-value]

    with pytest.raises(TypeError):
        editor_loader.load_plugins([loader])
