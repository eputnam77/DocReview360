"""Implementation for task 194."""

from fastapi.testclient import TestClient

from ..api import app
from ..stubs import record_task_completion
from ..workflows import create_workflow


def task194() -> bool:
    """Exercise the start workflow endpoint."""

    wf = create_workflow("t194", ["draft", "review"])
    client = TestClient(app)
    resp = client.post(
        f"/workflows/{wf.id}/start",
        data={"title": "sample"},
    )
    record_task_completion(194)
    return resp.status_code == 200 and resp.json()["id"] == wf.id
