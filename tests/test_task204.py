from docreview360.stubs.task204 import task204


def test_task204_add_phase() -> None:
    """New phase should be appended if missing."""

    phases = ["Draft"]
    result = task204(phases, "Review")
    assert result == ["Draft", "Review"]
