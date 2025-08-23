"""Generate simple usage reports."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape
from typing import Any

from pydantic import BaseModel

from .approvals import approvals
from .documents import documents
from .search import _expire_temp_assignment, projects
from .status import internal_status
from .workflows import workflows


def compile_check_report(results: dict[str, Any]) -> tuple[bytes, bytes]:
    """Return HTML and PDF summaries of ``results``.

    Parameters
    ----------
    results:
        Mapping of check names to their outcomes.

    Returns
    -------
    tuple[bytes, bytes]
        HTML and PDF representations of the report.
    """

    rows = []
    for name, value in results.items():
        rows.append(f"<tr><th>{escape(str(name))}</th><td>{escape(str(value))}</td></tr>")
    html = (
        "<html><body><h1>Check Results</h1><table>" + "".join(rows) + "</table></body></html>"
    ).encode()
    pdf = f"PDF-PLACEHOLDER\n{html.decode()}".encode()
    return html, pdf


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


class ThroughputEntry(BaseModel):
    """Daily approval counts used for throughput charts."""

    date: str
    approvals: int


def throughput_data(days: int = 7) -> list[ThroughputEntry]:
    """Return approvals completed per day for the last ``days`` days."""

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days - 1)).date()
    counts: dict[str, int] = {}
    for a in approvals.values():
        if a.state == "approved" and a.signed_at:
            day = datetime.fromisoformat(a.signed_at).date()
            if day >= cutoff:
                counts[str(day)] = counts.get(str(day), 0) + 1
    return [ThroughputEntry(date=d, approvals=c) for d, c in sorted(counts.items())]


def throughput_csv(days: int = 7) -> str:
    """Return ``throughput_data`` as CSV string."""

    rows = throughput_data(days)
    lines = ["date,approvals"] + [f"{r.date},{r.approvals}" for r in rows]
    return "\n".join(lines) + "\n"


def workload_data() -> dict[str, int]:
    """Return project counts per assigned user."""

    counts: dict[str, int] = {}
    for p in projects.values():
        if p.user:
            counts[p.user] = counts.get(p.user, 0) + 1
    return counts


def workload_csv() -> str:
    """Return ``workload_data`` as CSV."""

    data = workload_data()
    lines = ["user,count"] + [f"{u},{c}" for u, c in data.items()]
    return "\n".join(lines) + "\n"


def doc_type_counts() -> dict[str, int]:
    """Return active project counts grouped by document type."""

    counts: dict[str, int] = {}
    for p in projects.values():
        if p.doc_type:
            counts[p.doc_type] = counts.get(p.doc_type, 0) + 1
    return counts


def user_dashboard(user: str) -> list[DashboardEntry]:
    """Return dashboard data scoped to ``user`` projects."""

    return dashboard_data(user)


def manager_dashboard() -> dict[str, Any]:
    """Return workload overview and project metrics for managers."""

    return {"workload": workload_data(), "projects": dashboard_data()}


def admin_dashboard() -> dict[str, Any]:
    """Return system health metrics and summary for administrators."""

    return {"summary": generate_summary(), "status": internal_status()}
