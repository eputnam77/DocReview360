from datetime import datetime, timedelta, timezone

from docreview360.hr_sync import sync_temp_reassignments
from docreview360.search import ProjectModel, projects


def test_sync_temp_reassignments() -> None:
    pid = "p123"
    projects[pid] = ProjectModel(id=pid, name="x")
    expiry = datetime.now(timezone.utc) + timedelta(days=1)
    records = [{"project": pid, "user": "bob", "until": expiry.isoformat()}]
    count = sync_temp_reassignments(records)
    assert count == 1
    assert projects[pid].temp_user == "bob"


def test_sync_temp_reassignments_naive_date() -> None:
    projects.clear()
    pid = "p124"
    projects[pid] = ProjectModel(id=pid, name="x")
    records = [{"project": pid, "user": "carol", "until": "2030-01-01"}]
    count = sync_temp_reassignments(records)
    assert count == 1
    assert projects[pid].temp_user == "carol"
