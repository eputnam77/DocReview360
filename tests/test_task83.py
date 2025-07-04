from docuflow.stubs.task83 import MetabaseClient


def test_get_chart() -> None:
    client = MetabaseClient()
    assert client.get_chart("42") == {"id": "42", "title": "Chart 42"}


def test_heatmap() -> None:
    client = MetabaseClient()
    data = client.heatmap("p1")
    assert data and len(data) == 3
