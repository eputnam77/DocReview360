from docreview360.stubs.task53 import task53


def test_task53_diff() -> None:
    diff = task53("a\nb\n", "a\nc\n")
    diff_text = "\n".join(diff)
    assert "-b" in diff_text
    assert "+c" in diff_text
