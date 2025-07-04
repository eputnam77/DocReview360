from fastapi.testclient import TestClient

from docuflow.api import app
from docuflow.reporting import summary_csv


def test_summary_csv_helper() -> None:
    csv = summary_csv()
    assert csv.startswith("projects")


def test_summary_csv_endpoint() -> None:
    client = TestClient(app)
    resp = client.get("/reports/summary.csv")
    assert resp.status_code == 200
    assert resp.text.startswith("projects")
