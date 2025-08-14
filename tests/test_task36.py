import pytest

from docreview360.ai_balancer import (
    assign_job,
    complete_job,
    current_load,
    register_worker,
    reset,
    deregister_worker,
)
from docreview360.ai_writer_assign import assign_technical_writer
from docreview360.config import Config
from docreview360.search import ProjectModel, add_project, projects


def test_balancer_assigns_least_loaded() -> None:
    reset()
    register_worker("a")
    register_worker("b")
    assert assign_job() == "a"
    assert assign_job() == "b"
    assert current_load("a") == 1
    assert current_load("b") == 1
    complete_job("a")
    assert assign_job() == "a"


def test_writer_assignment_updates_balancer() -> None:
    reset()
    snapshot = {pid: proj.model_copy() for pid, proj in projects.items()}
    try:
        projects.clear()
        add_project(ProjectModel(id="p1", name="A", user="alice"))
        add_project(ProjectModel(id="p2", name="B"))
        cfg = Config(
            database="sqlite",
            editor="tiptap",
            cms="none",
            auth="oidc",
            ai_auto_assign_writers=True,
        )
        chosen = assign_technical_writer("p2", ["alice", "bob"], cfg)
        assert chosen == "bob"
        assert current_load("alice") == 1
        assert current_load("bob") == 1
    finally:
        projects.clear()
        for pid, proj in snapshot.items():
            projects[pid] = proj
        reset()


def test_deregister_worker_returns_outstanding_load() -> None:
    reset()
    register_worker("alice")
    register_worker("bob")
    # Create some load across workers
    for _ in range(5):
        assign_job()
    load = deregister_worker("alice")
    assert load == 3
    with pytest.raises(KeyError):
        current_load("alice")
    assert current_load("bob") == 2
