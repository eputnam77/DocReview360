from docreview360.stubs.task89 import merge_docs


def test_merge_docs() -> None:
    assert merge_docs("abc", "abcd") == "abcd"
