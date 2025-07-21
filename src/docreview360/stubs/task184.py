"""Implementation for task 184."""

from fastapi.testclient import TestClient

from ..api import app
from ..stubs import record_task_completion


def task184() -> bool:
    """Check throughput and workload endpoints."""

    client = TestClient(app)
    tp = client.get("/reports/throughput")
    wl = client.get("/reports/workload")
    record_task_completion(184)
    return tp.status_code == 200 and wl.status_code == 200
