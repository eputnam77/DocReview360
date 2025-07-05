from datetime import datetime, timedelta

from docuflow.hr_sync import sync_temp_reassignments
from docuflow.search import ProjectModel, projects


def test_sync_temp_reassignments() -> None:
    pid = "p123"
    projects[pid] = ProjectModel(id=pid, name="x")
    expiry = datetime.utcnow() + timedelta(days=1)
    records = [{"project": pid, "user": "bob", "until": expiry.isoformat()}]
    count = sync_temp_reassignments(records)
    assert count == 1
    assert projects[pid].temp_user == "bob"
