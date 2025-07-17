"""Manager dashboard endpoint sanity check."""

from fastapi.testclient import TestClient

from ..api import app
from ..stubs import record_task_completion


def task190() -> bool:
    """Verify manager dashboard returns data."""

    client = TestClient(app)
    resp = client.get("/dashboard/manager")
    record_task_completion(190)
    return resp.status_code == 200 and isinstance(resp.json(), list)
