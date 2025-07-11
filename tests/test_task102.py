from docreview360.editor_loader import load_plugins


def test_load_plugins() -> None:
    def a() -> str:
        return "a"

    def b() -> str:
        return "b"

    names = load_plugins([a, b])
    assert names == ["a", "b"]
