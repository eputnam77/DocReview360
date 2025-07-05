from docuflow.stubs.task88 import execute_query


def test_execute_query_projects() -> None:
    result = execute_query("{ projects { id name } }")
    assert result["projects"]


def test_execute_query_documents() -> None:
    result = execute_query("{ documents { id content } }")
    assert result["documents"]
