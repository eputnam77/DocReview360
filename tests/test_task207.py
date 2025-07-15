from docreview360.stubs.task207 import task207


def test_task207_validate_fields() -> None:
    """Both phase and workflow must exist."""

    assert task207({"phase": "Draft", "workflow": "std"})
