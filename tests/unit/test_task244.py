from docreview360.stubs.task244 import is_heading_edit_allowed


def test_task244_blocks_h1() -> None:
    assert not is_heading_edit_allowed(1)
