from docreview360.stubs.task218 import send_for_review


def test_task218_writer_can_send_for_review() -> None:
    """Writers should be able to send documents for review."""
    send_for_review("writer", "doc1")
