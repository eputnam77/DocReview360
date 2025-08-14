from docreview360.stubs.task52 import task52


def test_task52_generates_template() -> None:
    tpl = task52("sample")
    assert "terraform" in tpl
    assert "sample-data" in tpl
