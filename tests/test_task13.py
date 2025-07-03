from datetime import datetime, timedelta

from docuflow import search


def test_priority_and_temp_assignment() -> None:
    search.projects.clear()
    proj = search.ProjectModel(id="p13", name="Task 13", user="alice")
    search.add_project(proj)

    search.set_project_priority("p13", 5)
    project = search.get_project("p13")
    assert project.priority == 5

    past = datetime.utcnow() - timedelta(days=1)
    search.assign_temporary("p13", "bob", past)
    project = search.get_project("p13")
    assert project.temp_user is None
    assert project.user == "alice"

    future = datetime.utcnow() + timedelta(hours=1)
    search.assign_temporary("p13", "carol", future)
    project = search.get_project("p13")
    assert project.temp_user == "carol"

    project.temp_until = datetime.utcnow() - timedelta(seconds=1)
    project = search.get_project("p13")
    assert project.temp_user is None
    assert project.user == "alice"
