from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import pytest
from docreview360 import search


def test_load_state_clears_missing_workflow(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    repo = search.SearchRepository(str(tmp_path / "state.db"))
    project = search.ProjectModel(id="p1", name="Project", workflow="wf-missing")
    repo.save_project(project)

    with caplog.at_level(logging.WARNING):
        projects, _, _, _ = repo.load_state()

    assert projects["p1"].workflow is None
    assert "wf-missing" in caplog.text

    with repo._connection() as conn:
        row = conn.execute("SELECT payload FROM projects WHERE id = ?", ("p1",)).fetchone()
        assert row is not None
        stored = search.ProjectModel.model_validate_json(row["payload"])
        assert stored.workflow is None


def test_load_state_backfills_saved_search_user(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    repo = search.SearchRepository(str(tmp_path / "state.db"))
    created = datetime.now(UTC)
    with repo._connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO saved_searches (id, query, user, created, count, flagged)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("legacy", "orphan", None, created.isoformat(), 0, 0),
        )

    with caplog.at_level(logging.WARNING):
        _, saved, _, _ = repo.load_state()

    record = saved["legacy"]
    assert record.user == "unknown"
    assert record.flagged_for_review is True
    assert "legacy" in caplog.text

    with repo._connection() as conn:
        row = conn.execute(
            "SELECT user, flagged FROM saved_searches WHERE id = ?", ("legacy",)
        ).fetchone()
        assert row["user"] == "unknown"
        assert row["flagged"] == 1


def test_save_search_requires_user(monkeypatch: pytest.MonkeyPatch) -> None:
    search._reset_state_for_testing()
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def _log_event(*args: object, **kwargs: object) -> None:
        calls.append((args, kwargs))

    monkeypatch.setattr(search, "log_event", _log_event)

    try:
        with pytest.raises(ValueError):
            search.save_search("terms", user=" ")

        record = search.save_search("terms", user="alice")
        assert record.user == "alice"
        assert calls
        action_args, action_kwargs = calls[-1]
        assert action_args[0] == "saved_search_created"
        assert action_kwargs["user_id"] == "alice"
        assert action_kwargs["entity_id"] == record.id
    finally:
        search._reset_state_for_testing()
