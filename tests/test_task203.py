from docreview360.stubs.task203 import task203


def test_task203_merge_config() -> None:
    """Merging config should set defaults."""

    cfg = task203({"slack": True})
    assert cfg["slack"] is True and cfg["github"] is True
