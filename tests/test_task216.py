from docreview360.stubs.task216 import toggle_watch


def test_task216_toggle() -> None:
    # first toggle adds project
    lst1 = toggle_watch("alice", "p1")
    assert "p1" in lst1
    # second toggle removes
    lst2 = toggle_watch("alice", "p1")
    assert "p1" not in lst2
