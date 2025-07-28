from docreview360.stubs.task250 import load_projects


def test_task250_returns_sample() -> None:
    assert load_projects(False)
