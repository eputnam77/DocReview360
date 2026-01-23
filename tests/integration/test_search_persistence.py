import importlib
import threading
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import docreview360.search as search


def _prepare_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "search-state.db"
    monkeypatch.setenv("DOCREVIEW360_SEARCH_DB", str(db_path))
    search._reset_state_for_testing(db_path=db_path)
    return db_path


@contextmanager
def _reloaded_search() -> None:
    original_state = {
        "repository": search._repository,
        "search_index": search.search_index,
        "saved_searches": search.saved_searches,
        "search_counter": search.search_counter,
        "project_lock": search.project_lock,
        "saved_search_lock": search.saved_search_lock,
        "counter_lock": search.counter_lock,
        "index_lock": search.index_lock,
    }
    reloaded = importlib.reload(search)
    try:
        yield reloaded
    finally:
        search._repository = original_state["repository"]
        search.search_index = original_state["search_index"]
        search.projects = search.search_index.projects
        search.saved_searches = original_state["saved_searches"]
        search.search_counter = original_state["search_counter"]
        search.project_lock = original_state["project_lock"]
        search.saved_search_lock = original_state["saved_search_lock"]
        search.counter_lock = original_state["counter_lock"]
        search.index_lock = original_state["index_lock"]
        search._reload_state_from_repository()


def test_projects_and_searches_survive_reload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prepare_db(tmp_path, monkeypatch)

    import docreview360.workflows as workflows_module

    workflows_module.workflows.clear()

    project = search.ProjectModel(id="persist", name="Persisted", doc_type="Report")
    search.add_project(project)
    wf = workflows_module.create_workflow("persist", ["draft"])
    search.update_project("persist", name="Persisted v2", workflow=wf.id, workflow_set=True)
    future = datetime.now(UTC) + timedelta(days=1)
    search.assign_temporary("persist", "temp-user", future)
    search.save_search("persist query", user="bob")
    search.search("persist query")

    with _reloaded_search() as reloaded:
        loaded = reloaded.projects["persist"]
        assert loaded.name == "Persisted v2"
        assert loaded.workflow == wf.id
        assert loaded.temp_user == "temp-user"
        assert reloaded.list_saved_searches(user="bob")[0].query == "persist query"
        assert reloaded.search_stats()["persist query"] >= 1

        # Ensure the project number and repository metadata were preserved.
        assert loaded.number == project.number
        assert reloaded.next_project_number() == (project.number or 0) + 1


def test_concurrent_project_creation_persists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prepare_db(tmp_path, monkeypatch)

    created_ids = [f"proj-{idx}" for idx in range(5)]
    barrier = threading.Barrier(len(created_ids))

    def worker(identifier: str) -> None:
        barrier.wait()
        new_project = search.ProjectModel(id=identifier, name=f"Project {identifier}")
        search.add_project(new_project)

    threads = [threading.Thread(target=worker, args=(identifier,)) for identifier in created_ids]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    numbers = {search.projects[identifier].number for identifier in created_ids}
    assert len(numbers) == len(created_ids)
    assert sorted(numbers) == list(range(2, 2 + len(created_ids)))

    with _reloaded_search() as reloaded:
        numbers_after_reload = [reloaded.projects[identifier].number for identifier in created_ids]
        assert sorted(numbers_after_reload) == sorted(numbers)

        expected_next = max(numbers_after_reload) + 1
        assert reloaded.next_project_number() == expected_next


def test_missing_workflow_reference_clears_on_reload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prepare_db(tmp_path, monkeypatch)

    import docreview360.workflows as workflows_module

    workflows_module.workflows.clear()

    project = search.ProjectModel(id="ghost-project", name="Ghost", workflow="ghost-wf")
    search.add_project(project)

    with _reloaded_search() as reloaded:
        loaded = reloaded.projects["ghost-project"]
        assert loaded.workflow is None
        assert loaded.requested_workflow == "ghost-wf"
