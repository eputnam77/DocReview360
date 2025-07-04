from docuflow.stubs.task87 import render_chart


def test_render_chart() -> None:
    yaml = render_chart("app", {"replicas": 2})
    assert "app:" in yaml and "replicas: 2" in yaml
