from docreview360.stubs.task205 import task205


def test_task205_edit_comment() -> None:
    """Comment text should be updated."""

    assert task205("old", "new") == "new"
