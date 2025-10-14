from fastapi.testclient import TestClient

from docreview360.api import app
from docreview360.reporting import summary_csv


def test_summary_csv_helper() -> None:
    csv = summary_csv()
    assert csv.startswith("projects")
    header = csv.splitlines()[0]
    assert "avg_quality_score" in header


def test_summary_csv_endpoint() -> None:
    client = TestClient(app)
    resp = client.get("/reports/summary.csv")
    assert resp.status_code == 200
    assert resp.text.startswith("projects")
