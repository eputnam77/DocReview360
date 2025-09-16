"""Validate timestamp defaults in the search models."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from docreview360 import search


def test_project_model_created_timestamp_is_unique(monkeypatch) -> None:
    """Two projects created in succession should receive distinct timestamps."""

    real_datetime = search.datetime

    class _StubDateTime:
        _counter = 0

        @classmethod
        def now(cls, tz: object | None = None) -> datetime:
            base = real_datetime(2024, 5, 1, tzinfo=UTC)
            value = base + timedelta(seconds=cls._counter)
            cls._counter += 1
            return value

        def __getattr__(self, name: str):  # pragma: no cover - defensive
            return getattr(real_datetime, name)

    monkeypatch.setattr(search, "datetime", _StubDateTime)

    first = search.ProjectModel(id="p1", name="One")
    second = search.ProjectModel(id="p2", name="Two")

    assert first.created != second.created


def test_saved_search_created_timestamp_is_unique(monkeypatch) -> None:
    """Each saved search should capture creation time independently."""

    real_datetime = search.datetime

    class _StubDateTime:
        _counter = 0

        @classmethod
        def now(cls, tz: object | None = None) -> datetime:
            base = real_datetime(2024, 6, 1, tzinfo=UTC)
            value = base + timedelta(minutes=cls._counter)
            cls._counter += 1
            return value

        def __getattr__(self, name: str):  # pragma: no cover - defensive
            return getattr(real_datetime, name)

    monkeypatch.setattr(search, "datetime", _StubDateTime)

    first = search.SavedSearch(id="s1", query="foo")
    second = search.SavedSearch(id="s2", query="bar")

    assert first.created != second.created


def test_list_projects_handles_naive_temp_until() -> None:
    """Temporary assignments with naive timestamps should expire safely."""

    project = search.ProjectModel(id="temp", name="Temp")
    project.temp_user = "reviewer"
    project.temp_until = datetime(2020, 1, 1)  # Naive past timestamp
    original = search.projects.copy()
    try:
        search.projects[project.id] = project
        # The call previously raised ``TypeError`` when comparing a naive
        # ``temp_until`` against the timezone-aware ``datetime.now(UTC)``.
        search.list_projects()
        assert project.temp_user is None
        assert project.temp_until is None
    finally:
        search.projects.clear()
        search.projects.update(original)
