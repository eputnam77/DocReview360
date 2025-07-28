from docreview360.stubs.task249 import start_yjs_collaboration


def test_task249_starts_collab() -> None:
    assert start_yjs_collaboration("doc1") is True
