from datetime import datetime, timedelta

import pytest
from docuflow.search import ProjectModel, assign_temporary, projects


def test_manager_approval_required() -> None:
    proj = ProjectModel(id="pY", name="Test")
    projects[proj.id] = proj
    long_until = datetime.utcnow() + timedelta(days=40)
    with pytest.raises(ValueError):
        assign_temporary(proj.id, "temp", long_until)
    assign_temporary(proj.id, "temp", long_until, approved=True)
    assert projects[proj.id].temp_user == "temp"
