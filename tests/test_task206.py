from docreview360.stubs.task206 import task206


def test_task206_single_call() -> None:
    """Ensure callable executed exactly once."""

    called = 0

    def check() -> str:
        nonlocal called
        called += 1
        return "ok"

    result = task206(check)
    assert result == "ok" and called == 1
