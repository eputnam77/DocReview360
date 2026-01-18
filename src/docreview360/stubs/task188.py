"""Profile page API sanity check (Task 188)."""

from fastapi.testclient import TestClient

from .. import auth
from ..api import app
from ..stubs import record_task_completion


def task188() -> bool:
    """Exercise the profile endpoints."""

    client = TestClient(app)
    token = auth.create_access_token({"sub": "bob"})
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/profile", headers=headers)
    if resp.status_code != 200 or resp.json()["username"] != "bob":
        return False
    resp = client.put(
        "/profile",
        json={"theme": "dark"},
        headers=headers,
    )
    record_task_completion(188)
    return resp.status_code == 200 and resp.json()["preferences"]["theme"] == "dark"
