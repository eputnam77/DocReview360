from docuflow.plugins import registry


def sample_plugin() -> str:
    return "ok"


def test_plugin_registry() -> None:
    registry.register("sample", sample_plugin)
    assert registry.get("sample")() == "ok"
    assert "sample" in registry.all()
