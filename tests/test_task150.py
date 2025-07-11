from docreview360.stubs.task150 import task150


def test_task150_completed() -> None:
    issues = task150("bad bad text")
    assert issues
