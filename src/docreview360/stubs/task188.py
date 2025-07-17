"""Profile page API sanity check (Task 188)."""

from fastapi.testclient import TestClient

from ..api import app
from ..stubs import record_task_completion


def task188() -> bool:
    """Exercise the profile endpoints."""

    client = TestClient(app)
    resp = client.get("/profile", headers={"X-User": "bob"})
    if resp.status_code != 200 or resp.json()["username"] != "bob":
        return False
    resp = client.put(
        "/profile",
        json={"dark_mode": True},
        headers={"X-User": "bob"},
    )
    record_task_completion(188)
    return resp.status_code == 200 and resp.json()["preferences"]["dark_mode"]
