from __future__ import annotations

from pydantic import BaseModel

from .approvals import approvals
from .documents import documents
from .search import _expire_temp_assignment, projects
from .workflows import workflows


class SummaryReport(BaseModel):
    """Aggregated counts for overall system state."""

    projects: int
    documents: int
    workflows: int
    approvals: int


class DashboardEntry(BaseModel):
    """Per-project metrics used by the dashboard."""

    id: str
    name: str
    priority: int
    phase: str | None = None
    docs: int = 0
    pending_approvals: int = 0


def generate_summary() -> SummaryReport:
    """Return counts of key objects."""
    return SummaryReport(
        projects=len(projects),
        documents=len(documents),
        workflows=len(workflows),
        approvals=len(approvals),
    )


def dashboard_data(user: str | None = None) -> list[DashboardEntry]:
    """Return per-project dashboard metrics.

    When ``user`` is provided the results are scoped to projects assigned to
    that user either permanently or temporarily.
    """

    data: list[DashboardEntry] = []
    for project in projects.values():
        _expire_temp_assignment(project)
        if user and project.user != user and project.temp_user != user:
            continue
        doc_count = sum(1 for d in documents.values() if d.project == project.id)
        wf = next((w for w in workflows.values() if w.project == project.id), None)
        pending = sum(
            1
            for a in approvals.values()
            if wf is not None and a.workflow == wf.id and a.state == "pending"
        )
        data.append(
            DashboardEntry(
                id=project.id,
                name=project.name,
                priority=project.priority,
                phase=wf.phase if wf else None,
                docs=doc_count,
                pending_approvals=pending,
            )
        )
    return data


def widget_counts(user: str | None = None) -> dict[str, int]:
    """Return counts used by dashboard widgets.

    If ``user`` is provided the counts are restricted to that user.
    """

    if user is None:
        assigned = sum(1 for p in projects.values() if p.user or p.temp_user)
        active = sum(1 for p in projects.values() if p.temp_user)
        pending = sum(1 for a in approvals.values() if a.state == "pending")
    else:
        assigned = sum(1 for p in projects.values() if p.user == user or p.temp_user == user)
        active = sum(1 for p in projects.values() if p.temp_user == user)
        pending = sum(1 for a in approvals.values() if a.state == "pending" and a.reviewer == user)
    return {"assigned": assigned, "active": active, "pending_approvals": pending}


def summary_csv() -> str:
    """Return ``generate_summary`` as a single-line CSV string."""
    summary = generate_summary()
    return (
        "projects,documents,workflows,approvals\n"
        f"{summary.projects},{summary.documents},{summary.workflows},{summary.approvals}\n"
    )
