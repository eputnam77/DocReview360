from docreview360 import comments
from docreview360.stubs.task24 import task24


def test_task24_comment_thread() -> None:
    comments._comments.clear()
    length = task24("d1", "alice", "First comment")
    assert length == 1
    length = task24("d1", "bob", "Reply")
    assert length == 2
