from docreview360.stubs.task245 import apply_indent


def test_task245_indent_increases() -> None:
    assert apply_indent(0, "indent") == 1
