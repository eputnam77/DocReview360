from docuflow.stubs.task154 import task154


def test_task154_completed() -> None:
    html = task154("/gql")
    assert "/gql" in html
