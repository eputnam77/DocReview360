from docuflow.stubs.task82 import OpenSearchClient


def test_index_and_search() -> None:
    client = OpenSearchClient()
    client.index_document("hello world")
    assert client.search("hello") == ["hello world"]
