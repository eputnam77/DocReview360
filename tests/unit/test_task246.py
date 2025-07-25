from docreview360.stubs.task246 import validate_structure


def test_task246_rejects_bad() -> None:
    assert validate_structure(["h1", "h2", "h2"]) is False
