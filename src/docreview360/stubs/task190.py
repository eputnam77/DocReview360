"""Manager dashboard endpoint sanity check."""

import os

from fastapi.testclient import TestClient

from ..api import app
from ..rbac import add_role
from ..stubs import record_task_completion


def task190() -> bool:
    """Verify manager dashboard returns data."""

    # Set up authentication and manager role.  Some environments running the
    # tests may not have the required JWT settings configured.  To keep the
    # stub self‑contained we provide sensible defaults so token creation does
    # not fail with ``RuntimeError`` when environment variables are missing.
    os.environ.setdefault("DOCREVIEW360_SECRET_KEY", "dev-secret")
    os.environ.setdefault("DOCREVIEW360_ALGORITHM", "HS256")

    add_role("alice", "manager")
    client = TestClient(app)

    # Create a token for alice (using the sample user from auth.py)
    from .. import auth

    token = auth.create_access_token({"sub": "alice"})

    resp = client.get("/dashboard/manager", headers={"Authorization": f"Bearer {token}"})
    record_task_completion(190)
    data = resp.json()
    return (
        resp.status_code == 200
        and "workload" in data
        and "projects" in data
        and isinstance(data["projects"], list)
    )
