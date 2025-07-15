from docreview360.stubs.task201 import task201


def test_task201_chat_bot() -> None:
    """Chat bot should answer simple queries."""

    assert "on track" in task201("status of project")
