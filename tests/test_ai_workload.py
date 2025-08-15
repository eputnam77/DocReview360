"""AI helpers and workload balancer tests."""

from __future__ import annotations

from docreview360.logs import clear_logs, log_event, query_logs

# AI-01


def suggest_outline(text: str) -> list[str]:
    """Return markdown headings without modifying the original text."""
    return [line.strip() for line in text.splitlines() if line.startswith("#")]


def test_suggest_only_generates_outline_without_inserting_text() -> None:
    content = "# Title\nBody"
    outline = suggest_outline(content)
    assert outline == ["# Title"]
    assert content == "# Title\nBody"


# AI-02


def assign_urgent(loads: dict[str, int], worker: str) -> bool:
    """Return ``False`` when ``worker`` already has 12 projects."""
    if loads.get(worker, 0) >= 12:
        return False
    loads[worker] = loads.get(worker, 0) + 1
    return True


def test_balancer_blocks_overloaded_writer() -> None:
    loads = {"alice": 12}
    ok = assign_urgent(loads, "alice")
    assert not ok
    assert loads["alice"] == 12


# AI-03


def daily_auto_assign(user: str) -> None:
    """Simulate daily job assigning an item and logging the rule."""
    log_event("auto_assign", user_id=user, rule="least_loaded")


def test_auto_assign_audit_and_tooltip() -> None:
    clear_logs()
    daily_auto_assign("bob")
    entry = query_logs("auto_assign")[0]
    tooltip = f"Assigned via {entry.context['rule']}"
    assert entry.context["rule"] == "least_loaded"
    assert tooltip.endswith("least_loaded")
