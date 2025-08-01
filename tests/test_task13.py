from datetime import UTC, datetime, timedelta

from docreview360 import search


def test_priority_and_temp_assignment() -> None:
    """Test priority setting and temporary assignment functionality.

    This test was previously hanging due to a deadlock in _expire_temp_assignment()
    when called from functions that already hold the project_lock. The fix adds
    a lock_held parameter to prevent re-acquiring the same lock.
    """
    search.projects.clear()
    proj = search.ProjectModel(id="p13", name="Task 13", user="alice")
    search.add_project(proj)

    search.set_project_priority("p13", 5)
    project = search.get_project("p13")
    assert project is not None
    assert project.priority == 5

    past = datetime.now(UTC) - timedelta(days=1)
    search.assign_temporary("p13", "bob", past)
    project = search.get_project("p13")
    assert project is not None
    assert project.temp_user is None
    assert project.user == "alice"

    future = datetime.now(UTC) + timedelta(hours=1)
    search.assign_temporary("p13", "carol", future)
    project = search.get_project("p13")
    assert project is not None
    assert project.temp_user == "carol"

    project.temp_until = datetime.now(UTC) - timedelta(seconds=1)
    project = search.get_project("p13")
    assert project is not None
    assert project.temp_user is None
    assert project.user == "alice"


def test_threading_fix_no_deadlock() -> None:
    """
    Test that the threading fix prevents deadlocks when calling functions
    that use project_lock.
    """
    search.projects.clear()
    proj = search.ProjectModel(id="p14", name="Task 14", user="alice")
    search.add_project(proj)

    # Test that get_project doesn't deadlock
    project = search.get_project("p14")
    assert project is not None
    assert project.user == "alice"

    # Test that list_projects doesn't deadlock
    projects = search.list_projects()
    assert len(projects) == 1
    assert projects[0].id == "p14"

    # Test that overdue_high_priority doesn't deadlock
    overdue = search.overdue_high_priority()
    assert isinstance(overdue, list)
