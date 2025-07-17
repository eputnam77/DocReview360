"""Dashboard visibility API test (Task 189)."""

from fastapi.testclient import TestClient

from ..api import app
from ..stubs import record_task_completion


def task189() -> bool:
    """Check visibility endpoints."""

    client = TestClient(app)
    resp = client.put(
        "/dashboard/visibility",
        json={"stats": False},
        headers={"X-User": "bob"},
    )
    if resp.status_code != 200 or resp.json()["stats"] is not False:
        return False
    get_resp = client.get("/dashboard/visibility", headers={"X-User": "bob"})
    record_task_completion(189)
    return get_resp.json()["stats"] is False
