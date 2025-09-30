from datetime import UTC, datetime, timedelta

from docreview360.cache import clear_cache
from docreview360.documents import DocumentModel, documents
from docreview360.search import (
    ProjectModel,
    add_document,
    assign_temporary,
    get_project,
    list_projects,
    list_saved_searches,
    overdue_high_priority,
    projects,
    save_search,
    saved_searches,
    search,
    search_counter,
    search_index,
    search_stats,
    set_project_priority,
)


def test_search_workflow_and_saved_queries() -> None:
    # Reset global state for determinism
    documents.clear()
    projects.clear()
    search_index.index.clear()
    saved_searches.clear()
    search_counter.clear()

    # Add a project and document
    proj = ProjectModel(id="p1", name="Proj")
    search_index.add_project(proj)
    doc = DocumentModel(id="d1", content="hello world", project="p1")
    documents[doc.id] = doc
    add_document(doc)

    # Temporary assignment should expire when past
    assign_temporary("p1", "temp", datetime.now(UTC) - timedelta(days=1))
    assert get_project("p1").temp_user is None

    # Priority and overdue detection
    set_project_priority("p1", 5)
    proj.created = datetime.now(UTC) - timedelta(days=15)
    alerts = overdue_high_priority()
    assert "p1" in alerts

    # Saved searches and stats
    save_search("hello", user="system")
    save_search("hello", user="alice")
    assert len(list_saved_searches()) == 2
    assert len(list_saved_searches(user="alice")) == 1

    # Search results cached
    clear_cache()
    results = search("hello")
    assert [d.id for d in results] == ["d1"]
    # Cache hit path
    results_cached = search("hello")
    assert [d.id for d in results_cached] == ["d1"]

    # search() increments statistics
    stats = search_stats()
    assert stats["hello"] >= 2

    # list_projects should include project even without user filter
    assert any(p.id == "p1" for p in list_projects())
