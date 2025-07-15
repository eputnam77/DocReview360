from docreview360.stubs.task210 import task210


def test_task210_notification_text() -> None:
    """Notification message should include owner."""

    msg = task210("Bob", "Updated")
    assert "Bob" in msg and "Updated" in msg
