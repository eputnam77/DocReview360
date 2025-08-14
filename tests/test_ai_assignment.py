import pytest

from docreview360.ai_writer_assign import assign_technical_writer
from docreview360.config import Config
from docreview360.search import ProjectModel, add_project, projects


def _snapshot_projects():
    return {pid: proj.model_copy() for pid, proj in projects.items()}


def _restore_projects(snapshot):
    projects.clear()
    for pid, proj in snapshot.items():
        projects[pid] = proj


def test_assignment_picks_least_loaded_writer():
    snap = _snapshot_projects()
    try:
        add_project(ProjectModel(id="p1", name="A", user="alice", priority=1))
        add_project(ProjectModel(id="p2", name="B", user="bob", priority=3))
        add_project(ProjectModel(id="p3", name="C", priority=2))
        cfg = Config(database="sqlite", editor="tiptap", cms="none", auth="oidc", ai_auto_assign_writers=True)
        chosen = assign_technical_writer("p3", ["alice", "bob"], cfg)
        assert chosen == "alice"
        assert projects["p3"].user == "alice"
    finally:
        _restore_projects(snap)


def test_assignment_disabled_raises():
    snap = _snapshot_projects()
    try:
        add_project(ProjectModel(id="p4", name="D"))
        cfg = Config(database="sqlite", editor="tiptap", cms="none", auth="oidc", ai_auto_assign_writers=False)
        with pytest.raises(RuntimeError):
            assign_technical_writer("p4", ["alice"], cfg)
    finally:
        _restore_projects(snap)
