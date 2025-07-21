"""Implementation for task 186."""

from fastapi.testclient import TestClient

from ..api import app
from ..stubs import record_task_completion


def task186() -> bool:
    """Verify document type count endpoint."""

    client = TestClient(app)
    resp = client.get("/dashboard/doc-types")
    record_task_completion(186)
    return resp.status_code == 200
