import pytest

from docreview360.ai_writer_assign import (
    assign_technical_writer,
    reassign_projects_from_writer,
)
from docreview360.config import Config
from docreview360.search import ProjectModel, add_project, projects
from docreview360 import auth


def _cfg(enabled: bool = True) -> Config:
    return Config(
        database="sqlite",
        editor="tiptap",
        cms="none",
        auth="oidc",
        ai_auto_assign_writers=enabled,
    )


def test_assign_unknown_project_raises() -> None:
    with pytest.raises(ValueError):
        assign_technical_writer("missing", ["alice"], _cfg())


def test_assign_requires_active_candidates(monkeypatch) -> None:
    projects.clear()
    add_project(ProjectModel(id="pX", name="X"))
    monkeypatch.setattr(auth, "is_active", lambda _: False)
    with pytest.raises(ValueError):
        assign_technical_writer("pX", ["alice"], _cfg())


def test_reassign_disabled_raises() -> None:
    with pytest.raises(RuntimeError):
        reassign_projects_from_writer("alice", ["bob"], _cfg(enabled=False))


def test_reassign_no_candidates_raises() -> None:
    with pytest.raises(ValueError):
        reassign_projects_from_writer("alice", [], _cfg())


def test_reassign_handles_missing_worker() -> None:
    projects.clear()
    add_project(ProjectModel(id="p1", name="P", user="alice"))
    # ``alice`` is not registered with the balancer; the KeyError paths should be
    # exercised without raising.
    reassign_projects_from_writer("alice", ["bob"], _cfg())
