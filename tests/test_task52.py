from docreview360.stubs.task52 import task52


def test_task52_generates_template() -> None:
    tpl = task52("demo")
    assert "terraform" in tpl
    assert "demo-data" in tpl
