from docreview360.search import ProjectModel
from docreview360.stubs.task217 import apply_default_lead


def test_task217_apply_default_lead() -> None:
    project = ProjectModel(id="p1", name="Test")
    result = apply_default_lead(project, "alice")
    assert result.user == "alice"
    # Calling again with same user should keep value
    result2 = apply_default_lead(project, "bob")
    assert result2.user == "alice"
