from docuflow.stubs.task88 import execute_query


def test_execute_query_projects() -> None:
    result = execute_query("{ projects { id } }")
    assert "projects" in result
