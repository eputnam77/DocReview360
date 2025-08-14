import threading
from collections import Counter

import pytest

from docreview360 import ai_balancer
from docreview360.ai_writer_assign import (
    assign_technical_writer,
    reassign_projects_from_writer,
)
from docreview360.config import Config
from docreview360.search import ProjectModel, add_project, projects


def _snapshot_projects() -> dict[str, ProjectModel]:
    return {pid: proj.model_copy() for pid, proj in projects.items()}


def _restore_projects(snapshot: dict[str, ProjectModel]) -> None:
    projects.clear()
    for pid, proj in snapshot.items():
        projects[pid] = proj


def test_assignment_picks_least_loaded_writer() -> None:
    snap = _snapshot_projects()
    ai_balancer.reset()
    try:
        add_project(ProjectModel(id="p1", name="A", user="alice", priority=1))
        add_project(ProjectModel(id="p2", name="B", user="bob", priority=3))
        add_project(ProjectModel(id="p3", name="C", priority=2))
        cfg = Config(
            database="sqlite",
            editor="tiptap",
            cms="none",
            auth="oidc",
            ai_auto_assign_writers=True,
        )
        chosen = assign_technical_writer("p3", ["alice", "bob"], cfg)
        assert chosen == "alice"
        assert projects["p3"].user == "alice"
        assert ai_balancer.current_load("alice") == 2
        assert ai_balancer.current_load("bob") == 1
    finally:
        _restore_projects(snap)
        ai_balancer.reset()


def test_assignment_disabled_raises() -> None:
    snap = _snapshot_projects()
    ai_balancer.reset()
    try:
        add_project(ProjectModel(id="p4", name="D"))
        cfg = Config(
            database="sqlite",
            editor="tiptap",
            cms="none",
            auth="oidc",
            ai_auto_assign_writers=False,
        )
        with pytest.raises(RuntimeError):
            assign_technical_writer("p4", ["alice"], cfg)
    finally:
        _restore_projects(snap)
        ai_balancer.reset()


def test_concurrent_assignments_thread_safe() -> None:
    """Ensure concurrent assignments do not corrupt project workloads."""
    snap = _snapshot_projects()
    ai_balancer.reset()
    try:
        cfg = Config(
            database="sqlite",
            editor="tiptap",
            cms="none",
            auth="oidc",
            ai_auto_assign_writers=True,
        )

        project_ids = [f"t{i}" for i in range(20)]
        for pid in project_ids:
            add_project(ProjectModel(id=pid, name=pid))

        errors: list[Exception] = []
        assignments: list[str] = []

        def worker(pid: str) -> None:
            try:
                writer = assign_technical_writer(pid, ["alice", "bob"], cfg)
                assignments.append(writer)
            except Exception as exc:  # pragma: no cover - safety net
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(pid,)) for pid in project_ids]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"unexpected errors: {errors!r}"
        counts = Counter(assignments)
        assert sum(counts.values()) == len(project_ids)
        assert abs(counts.get("alice", 0) - counts.get("bob", 0)) <= 1
        assert ai_balancer.current_load("alice") == counts.get("alice", 0)
        assert ai_balancer.current_load("bob") == counts.get("bob", 0)
    finally:
        _restore_projects(snap)
        ai_balancer.reset()


def test_reassign_projects_from_departing_writer() -> None:
    snap = _snapshot_projects()
    ai_balancer.reset()
    try:
        projects.clear()
        add_project(ProjectModel(id="p1", name="A", user="alice"))
        add_project(ProjectModel(id="p2", name="B", user="alice"))
        add_project(ProjectModel(id="p3", name="C", user="bob"))
        cfg = Config(
            database="sqlite",
            editor="tiptap",
            cms="none",
            auth="oidc",
            ai_auto_assign_writers=True,
        )
        # Ensure balancer reflects current assignments
        ai_balancer.register_worker("alice")
        ai_balancer.register_worker("bob")
        ai_balancer.register_worker("carol")
        ai_balancer._workers["alice"] = 2  # type: ignore[attr-defined]
        ai_balancer._workers["bob"] = 1  # type: ignore[attr-defined]

        reassigned = reassign_projects_from_writer("alice", ["bob", "carol"], cfg)
        assert set(reassigned) == {"p1", "p2"}
        assert all(proj.user != "alice" for proj in projects.values())
        counts = Counter(proj.user for proj in projects.values())
        assert ai_balancer.current_load("bob") == counts.get("bob", 0)
        assert ai_balancer.current_load("carol") == counts.get("carol", 0)
        with pytest.raises(KeyError):
            ai_balancer.current_load("alice")
    finally:
        _restore_projects(snap)
        ai_balancer.reset()
