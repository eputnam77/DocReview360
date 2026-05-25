# SPDX-License-Identifier: MIT
"""Dashboard, summary, and report generation functions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape
from typing import Any

from ..approvals import approvals
from ..documents import documents
from ..search import _expire_temp_assignment, list_projects, projects
from ..status import internal_status
from ..workflows import workflows
from ._metrics import (
    _DEFAULT_LATENCY_BUCKETS,
    _PROJECT_METRICS,
    _aggregate_for_projects,
    _format_optional,
    _metadata_snapshot,
    _routing_latency_snapshot,
    _sanitize_column,
)
from ._models import (
    DashboardEntry,
    DocumentAgingEntry,
    DocumentAgingReport,
    ReviewerWorkload,
    SummaryReport,
    ThroughputEntry,
    WidgetMetrics,
)


def compile_check_report(results: dict[str, Any]) -> tuple[bytes, bytes]:
    """Return HTML and PDF summaries of ``results``."""

    rows = []
    for name, value in results.items():
        rows.append(f"<tr><th>{escape(str(name))}</th><td>{escape(str(value))}</td></tr>")
    html = (
        "<html><body><h1>Check Results</h1><table>" + "".join(rows) + "</table></body></html>"
    ).encode()
    pdf = f"PDF-PLACEHOLDER\n{html.decode()}".encode()
    return html, pdf


def reviewer_workload_dashboard() -> list[ReviewerWorkload]:  # noqa: C901
    """Return per-reviewer workload metrics across all approvals."""
    from ..review_assignments import TERMINAL_STATUSES, list_assignments

    # Snapshot shared dicts to avoid RuntimeError if concurrent writes modify
    # them while we iterate.
    approvals_snap = list(approvals.values())
    projects_snap = list(projects.values())

    stats: dict[str, dict[str, int]] = {}
    for approval in approvals_snap:
        reviewer = approval.reviewer
        if reviewer not in stats:
            stats[reviewer] = {"pending": 0, "approved": 0, "overdue": 0, "rejected": 0}
        state = approval.state
        if state == "pending":
            stats[reviewer]["pending"] += 1
        elif state == "approved":
            stats[reviewer]["approved"] += 1
        elif state == "overdue":
            stats[reviewer]["overdue"] += 1
        elif state in {"rejected", "denied"}:
            stats[reviewer]["rejected"] += 1

    # Count active project engagements per reviewer. Use a set of (user, project_id)
    # pairs to avoid double-counting a user who is both the project owner and an
    # active reviewer on the same project.
    project_counts: dict[str, int] = {}
    for proj in projects_snap:
        seen: set[str] = set()
        if proj.user:
            project_counts[proj.user] = project_counts.get(proj.user, 0) + 1
            seen.add(proj.user)
        try:
            assignments = list_assignments(proj.id)
        except Exception:
            assignments = []
        for assignment in assignments:
            if assignment.status in TERMINAL_STATUSES:
                continue
            reviewer = assignment.reviewer
            if reviewer not in seen:
                project_counts[reviewer] = project_counts.get(reviewer, 0) + 1
                seen.add(reviewer)

    for reviewer in project_counts:
        stats.setdefault(
            reviewer,
            {"pending": 0, "approved": 0, "overdue": 0, "rejected": 0},
        )

    result: list[ReviewerWorkload] = []
    for reviewer, counts in stats.items():
        total = counts["pending"] + counts["approved"] + counts["overdue"] + counts["rejected"]
        result.append(
            ReviewerWorkload(
                reviewer=reviewer,
                pending_approvals=counts["pending"],
                approved_approvals=counts["approved"],
                overdue_approvals=counts["overdue"],
                rejected_approvals=counts["rejected"],
                total_approvals=total,
                assigned_projects=project_counts.get(reviewer, 0),
            )
        )
    result.sort(key=lambda r: r.pending_approvals, reverse=True)
    return result


def document_aging_metrics() -> DocumentAgingReport:
    """Compute aging metrics for all documents in the system."""

    now = datetime.now(timezone.utc)
    # Snapshot shared dicts before iterating to avoid RuntimeError from
    # concurrent modifications.
    approvals_snap = list(approvals.values())
    documents_snap = list(documents.values())

    pending_doc_ids: set[str] = set()
    overdue_doc_ids: set[str] = set()
    for approval in approvals_snap:
        if approval.state == "pending":
            pending_doc_ids.add(approval.document_id)
        elif approval.state == "overdue":
            overdue_doc_ids.add(approval.document_id)

    entries: list[DocumentAgingEntry] = []
    age_values: list[int] = []
    for doc in documents_snap:
        age_days: int | None = None
        if doc.date is not None:
            created = doc.date
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            delta = now - created
            age_days = max(0, delta.days)
            age_values.append(age_days)
        entries.append(
            DocumentAgingEntry(
                document_id=doc.id,
                project=doc.project,
                age_days=age_days,
                has_pending_approvals=doc.id in pending_doc_ids,
                has_overdue_approvals=doc.id in overdue_doc_ids,
            )
        )

    avg_age: float | None = sum(age_values) / len(age_values) if age_values else None
    oldest: int | None = max(age_values) if age_values else None
    older_30 = sum(1 for a in age_values if a > 30)
    older_90 = sum(1 for a in age_values if a > 90)
    return DocumentAgingReport(
        total_documents=len(documents),
        documents_with_known_age=len(age_values),
        avg_age_days=round(avg_age, 1) if avg_age is not None else None,
        oldest_age_days=oldest,
        documents_older_than_30_days=older_30,
        documents_older_than_90_days=older_90,
        entries=entries,
    )


def generate_summary() -> SummaryReport:
    """Return counts of key objects."""
    # Snapshot sizes atomically — never mutate global state on a read path.
    return SummaryReport(
        projects=len(projects),
        documents=len(documents),
        workflows=len(workflows),
        approvals=len(approvals),
    )


def dashboard_data(user: str | None = None) -> list[DashboardEntry]:  # noqa: C901
    """Return per-project dashboard metrics."""

    # Snapshot all shared dicts before iterating so that concurrent project/
    # approval/workflow writes cannot cause RuntimeError mid-iteration.
    projects_snap = list(projects.values())
    documents_snap = list(documents.values())
    approvals_snap = list(approvals.values())
    workflows_snap = list(workflows.values())

    # Expire temporary assignments on a copy of the list — never inside an
    # active dict iteration.
    for project in projects_snap:
        _expire_temp_assignment(project)

    data: list[DashboardEntry] = []
    routing_snapshot = _routing_latency_snapshot()
    visible_project_ids = {project.id for project in list_projects(user)} if user else None

    # Build lookup maps to avoid O(N²) per-project scans.
    wf_by_project: dict[str, Any] = {}
    for wf in workflows_snap:
        if wf.project and wf.project not in wf_by_project:
            wf_by_project[wf.project] = wf

    docs_by_project: dict[str, int] = {}
    for d in documents_snap:
        if d.project:
            docs_by_project[d.project] = docs_by_project.get(d.project, 0) + 1

    pending_by_wf: dict[str, int] = {}
    overdue_by_wf: dict[str, int] = {}
    for a in approvals_snap:
        if a.state == "pending":
            pending_by_wf[a.workflow] = pending_by_wf.get(a.workflow, 0) + 1
        elif a.state == "overdue":
            overdue_by_wf[a.workflow] = overdue_by_wf.get(a.workflow, 0) + 1

    for project in projects_snap:
        if visible_project_ids is not None and project.id not in visible_project_ids:
            continue
        wf = wf_by_project.get(project.id)
        metrics = _PROJECT_METRICS.get(project.id)
        quality_avg = metrics.quality.average() if metrics else None
        compliance_avg = metrics.compliance.average() if metrics else None
        wf_id = wf.id if wf else None
        data.append(
            DashboardEntry(
                id=project.id,
                name=project.name,
                priority=project.priority,
                doc_type=project.doc_type,
                phase=wf.phase if wf else None,
                status=project.status,
                docs=docs_by_project.get(project.id, 0),
                pending_approvals=pending_by_wf.get(wf_id, 0) if wf_id else 0,
                overdue_approvals=overdue_by_wf.get(wf_id, 0) if wf_id else 0,
                quality_score=quality_avg,
                compliance_score=compliance_avg,
                routing_latency=routing_snapshot.copy(),
                critic_models=_metadata_snapshot(metrics),
            )
        )
    return data


def widget_counts(user: str | None = None) -> WidgetMetrics:
    """Return counts used by dashboard widgets."""
    from ..review_assignments import TERMINAL_STATUSES, list_assignments

    for proj in projects.values():
        _expire_temp_assignment(proj)

    def _active_assignment_count(project_ids: set[str], reviewer: str | None = None) -> int:
        total = 0
        for project_id in project_ids:
            try:
                assignments = list_assignments(project_id)
            except Exception:
                continue
            for assignment in assignments:
                if reviewer and assignment.reviewer != reviewer:
                    continue
                if assignment.status in TERMINAL_STATUSES:
                    continue
                total += 1
        return total

    if user is None:
        scoped_projects = list_projects()
        project_ids = {project.id for project in scoped_projects}
        assigned = sum(1 for p in scoped_projects if p.user or p.temp_user)
        active = (
            sum(1 for p in scoped_projects if p.temp_user) + _active_assignment_count(project_ids)
        )
        pending = sum(1 for a in approvals.values() if a.state == "pending")
        metrics = _PROJECT_METRICS.get(None)
    else:
        scoped_projects = list_projects(user)
        project_ids = {project.id for project in scoped_projects}
        assigned = len(scoped_projects)
        active = (
            sum(1 for p in scoped_projects if p.temp_user == user)
            + _active_assignment_count(project_ids, user)
        )
        pending = sum(
            1 for a in approvals.values() if a.state == "pending" and a.reviewer == user
        )
        pending += _active_assignment_count(project_ids, user)
        metrics = _aggregate_for_projects(project_ids)
    return WidgetMetrics(
        assigned=assigned,
        active=active,
        pending_approvals=pending,
        avg_quality_score=metrics.quality.average() if metrics else None,
        avg_compliance_score=metrics.compliance.average() if metrics else None,
        routing_latency=_routing_latency_snapshot(),
        critic_models=_metadata_snapshot(metrics),
    )


def summary_csv() -> str:
    """Return ``generate_summary`` as a single-line CSV string."""

    summary = generate_summary()
    metrics = _PROJECT_METRICS.get(None)
    quality_avg = metrics.quality.average() if metrics else None
    compliance_avg = metrics.compliance.average() if metrics else None
    metadata = _metadata_snapshot(metrics)
    latency = _routing_latency_snapshot()

    headers = [
        "projects",
        "documents",
        "workflows",
        "approvals",
        "avg_quality_score",
        "avg_compliance_score",
    ]
    values = [
        str(summary.projects),
        str(summary.documents),
        str(summary.workflows),
        str(summary.approvals),
        _format_optional(quality_avg),
        _format_optional(compliance_avg),
    ]

    for critic in sorted(metadata):
        details = metadata[critic]
        for key in sorted(details):
            headers.append(f"{critic}_{_sanitize_column(key)}")
            values.append(details[key])

    base_buckets = list(_DEFAULT_LATENCY_BUCKETS)
    extra_buckets = sorted(label for label in latency if label not in _DEFAULT_LATENCY_BUCKETS)
    for label in base_buckets + extra_buckets:
        headers.append(f"routing_latency_{_sanitize_column(label)}")
        values.append(str(latency.get(label, 0)))

    header_line = ",".join(headers)
    value_line = ",".join(values)
    return f"{header_line}\n{value_line}\n"


def throughput_data(days: int = 7) -> list[ThroughputEntry]:
    """Return approvals completed per day for the last ``days`` days."""

    if days <= 0:
        raise ValueError("days must be positive")
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days - 1)).date()
    counts: dict[str, int] = {}
    for a in approvals.values():
        if a.state == "approved" and a.signed_at:
            if isinstance(a.signed_at, str):
                day = datetime.fromisoformat(a.signed_at).date()
            else:
                day = a.signed_at.date()
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
    from ..review_assignments import TERMINAL_STATUSES, list_assignments

    counts: dict[str, int] = {}
    for p in list(projects.values()):
        # Track which users have already been counted for this project to avoid
        # double-counting an owner who also holds an active review assignment.
        seen: set[str] = set()
        if p.user:
            counts[p.user] = counts.get(p.user, 0) + 1
            seen.add(p.user)
        try:
            assignments = list_assignments(p.id)
        except Exception:
            assignments = []
        for assignment in assignments:
            if assignment.status in TERMINAL_STATUSES:
                continue
            if assignment.reviewer not in seen:
                counts[assignment.reviewer] = counts.get(assignment.reviewer, 0) + 1
                seen.add(assignment.reviewer)
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


def avg_quality_score() -> dict[str, Any]:
    """Return aggregate quality score metrics derived from in-memory documents.

    Queries all documents with a non-null ``last_quality_score`` and returns:

    * ``avg_score`` — average quality score across scored documents (0.0 when none).
    * ``docs_with_scores`` — count of documents that have been scored.
    * ``high_quality_count`` — documents with score >= 80 (i.e. >= 0.80 normalised).
    * ``needs_improvement_count`` — documents with score < 60 (i.e. < 0.60 normalised).

    Scores are stored in the range [0, 1]; the thresholds compare against those
    fractional values (0.80 and 0.60 respectively) so that callers can multiply by
    100 when displaying a percentage.
    """
    scored = [d.last_quality_score for d in documents.values() if d.last_quality_score is not None]
    if not scored:
        return {
            "avg_score": 0.0,
            "docs_with_scores": 0,
            "high_quality_count": 0,
            "needs_improvement_count": 0,
        }
    avg = sum(scored) / len(scored)
    high = sum(1 for s in scored if s >= 0.80)
    needs = sum(1 for s in scored if s < 0.60)
    return {
        "avg_score": round(avg, 4),
        "docs_with_scores": len(scored),
        "high_quality_count": high,
        "needs_improvement_count": needs,
    }


def user_dashboard(user: str) -> dict[str, Any]:
    """Return dashboard data scoped to ``user`` projects."""

    return {"projects": dashboard_data(user), "quality": avg_quality_score()}


def manager_dashboard() -> dict[str, Any]:
    """Return workload overview and project metrics for managers."""

    return {
        "workload": workload_data(),
        "projects": dashboard_data(),
        "quality": avg_quality_score(),
    }


def admin_dashboard() -> dict[str, Any]:
    """Return system health metrics and summary for administrators."""

    return {
        "summary": generate_summary(),
        "status": internal_status(),
        "quality": avg_quality_score(),
    }


def _to_aware_dt(value: Any) -> datetime | None:
    """Parse a datetime value and ensure it is UTC-aware."""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            return None
    elif isinstance(value, datetime):
        dt = value
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def analytics_dashboard(  # noqa: C901
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict[str, Any]:
    """Return comprehensive analytics data for the analytics dashboard.

    Parameters
    ----------
    start_date:
        Optional inclusive lower bound for date-filtered metrics.
    end_date:
        Optional inclusive upper bound for date-filtered metrics.
    """
    now = datetime.now(timezone.utc)
    _start = start_date or (now - timedelta(days=30))
    _end = end_date or now

    # Snapshot all shared dicts up-front to avoid RuntimeError from concurrent
    # modifications and to ensure a consistent view across all metrics.
    documents_snap = list(documents.values())
    approvals_snap = list(approvals.values())
    workflows_snap = list(workflows.values())
    projects_snap = list(projects.values())

    # Build O(1) lookup maps so inner loops are O(1) instead of O(N).
    wf_by_id = {wf.id: wf for wf in workflows_snap}
    proj_by_workflow = {p.workflow: p for p in projects_snap if p.workflow}

    # ---- document_stats ------------------------------------------------
    total_docs = len(documents_snap)
    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}
    age_values: list[float] = []
    for doc in documents_snap:
        status_key = getattr(doc, "status", None) or "unknown"
        by_status[status_key] = by_status.get(status_key, 0) + 1
        type_key = getattr(doc, "doc_type", None) or "unknown"
        by_type[type_key] = by_type.get(type_key, 0) + 1
        if doc.date is not None:
            created = _to_aware_dt(doc.date)
            if created:
                age_values.append((now - created).total_seconds() / 86400)
    avg_age = round(sum(age_values) / len(age_values), 1) if age_values else 0.0

    # ---- review_stats --------------------------------------------------
    total_reviews = len(approvals_snap)
    completion_days: list[float] = []
    on_time_count = 0
    approved_count = 0
    for a in approvals_snap:
        if a.state == "approved":
            approved_count += 1
        if a.state == "approved" and a.signed_at:
            signed_dt = _to_aware_dt(a.signed_at)
            if signed_dt is None:
                continue
            if a.deadline:
                deadline_dt = _to_aware_dt(a.deadline)
                if deadline_dt and signed_dt <= deadline_dt:
                    on_time_count += 1
            # O(1) lookup: workflow → project (was O(N²) nested loop)
            wf = wf_by_id.get(a.workflow)
            if wf:
                proj = proj_by_workflow.get(wf.id)
                if proj and proj.created:
                    created_dt = _to_aware_dt(proj.created)
                    if created_dt:
                        delta = (signed_dt - created_dt).total_seconds() / 86400
                        if delta >= 0:
                            completion_days.append(delta)
    avg_completion = (
        round(sum(completion_days) / len(completion_days), 1) if completion_days else 0.0
    )
    on_time_rate = round(on_time_count / approved_count, 3) if approved_count else 0.0

    # ---- user_activity -------------------------------------------------
    from ..logs import query_logs

    thirty_days_ago = now - timedelta(days=30)
    recent_logs = query_logs(start=thirty_days_ago, end=now, limit=10_000)
    active_users_set: set[str] = set()
    for entry in recent_logs:
        if entry.user_id:
            active_users_set.add(entry.user_id)
    total_actions_30d = len(recent_logs)

    # ---- quality_trends ------------------------------------------------
    quality_trends: list[dict[str, Any]] = []
    metrics_global = _PROJECT_METRICS.get(None)
    if metrics_global and metrics_global.quality.count:
        avg_q = metrics_global.quality.average()
        quality_trends.append({"date": now.date().isoformat(), "avg_score": round(avg_q or 0.0, 4)})

    # ---- phase_throughput ----------------------------------------------
    phase_throughput: list[dict[str, Any]] = []
    phase_counts: dict[str, list[float]] = {}
    # O(1) project lookup instead of O(N) inner scan
    proj_by_id = {p.id: p for p in projects_snap}
    for wf in workflows_snap:
        if wf.phase:
            if wf.phase not in phase_counts:
                phase_counts[wf.phase] = []
            if wf.project:
                proj = proj_by_id.get(wf.project)
                if proj and proj.created:
                    created_dt = _to_aware_dt(proj.created)
                    if created_dt:
                        phase_counts[wf.phase].append((now - created_dt).total_seconds() / 86400)
    for phase, days_list in sorted(phase_counts.items()):
        avg_days = round(sum(days_list) / len(days_list), 1) if days_list else 0.0
        phase_throughput.append({"phase": phase, "avg_days": avg_days, "count": len(days_list)})

    return {
        "generated_at": now.isoformat(),
        "period": {"start": _start.isoformat(), "end": _end.isoformat()},
        "document_stats": {
            "total": total_docs,
            "by_status": by_status,
            "by_type": by_type,
            "avg_age_days": avg_age,
        },
        "review_stats": {
            "total_reviews": total_reviews,
            "avg_completion_days": avg_completion,
            "on_time_rate": on_time_rate,
        },
        "user_activity": {
            "active_users": len(active_users_set),
            "total_actions_30d": total_actions_30d,
        },
        "quality_trends": quality_trends,
        "phase_throughput": phase_throughput,
    }


def analytics_export(
    fmt: str = "json",
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> tuple[str | bytes, str]:
    """Return analytics export data as (content, media_type).

    Parameters
    ----------
    fmt:
        ``"json"`` or ``"csv"``.
    start_date:
        Optional inclusive lower bound.
    end_date:
        Optional inclusive upper bound.
    """
    import csv
    import io

    data = analytics_dashboard(start_date=start_date, end_date=end_date)

    if fmt == "json":
        import json

        return json.dumps(data), "application/json"

    # CSV: flatten the top-level summary fields into rows
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["metric", "value"])

    doc_stats = data["document_stats"]
    writer.writerow(["total_documents", doc_stats["total"]])
    writer.writerow(["avg_age_days", doc_stats["avg_age_days"]])
    for status, count in doc_stats["by_status"].items():
        writer.writerow([f"docs_by_status_{status}", count])
    for doc_type, count in doc_stats["by_type"].items():
        writer.writerow([f"docs_by_type_{doc_type}", count])

    review_stats = data["review_stats"]
    writer.writerow(["total_reviews", review_stats["total_reviews"]])
    writer.writerow(["avg_completion_days", review_stats["avg_completion_days"]])
    writer.writerow(["on_time_rate", review_stats["on_time_rate"]])

    user_activity = data["user_activity"]
    writer.writerow(["active_users", user_activity["active_users"]])
    writer.writerow(["total_actions_30d", user_activity["total_actions_30d"]])

    for entry in data["quality_trends"]:
        writer.writerow([f"quality_trend_{entry['date']}", entry["avg_score"]])

    for entry in data["phase_throughput"]:
        writer.writerow([f"phase_{entry['phase']}_avg_days", entry["avg_days"]])
        writer.writerow([f"phase_{entry['phase']}_count", entry["count"]])

    return output.getvalue(), "text/csv"


def executive_summary() -> dict[str, Any]:
    """Return a high-level summary dashboard for leadership."""

    # Snapshot shared dicts before iterating.
    approvals_snap = list(approvals.values())
    workflows_snap = list(workflows.values())
    projects_snap = list(projects.values())
    documents_snap = list(documents.values())

    total_projects = len(projects_snap)
    active_projects = sum(
        True
        for p in projects_snap
        if p.status not in {"archived", "closed"}  # type: ignore[comparison-overlap]
    )

    total_approvals = len(approvals_snap)
    approved_count = sum(1 for a in approvals_snap if a.state == "approved")
    pending_count = sum(1 for a in approvals_snap if a.state == "pending")
    overdue_count = sum(1 for a in approvals_snap if a.state == "overdue")
    approval_rate = (approved_count / total_approvals * 100) if total_approvals else 0.0

    phase_distribution: dict[str, int] = {}
    for wf in workflows_snap:
        if wf.phase:
            phase_distribution[wf.phase] = phase_distribution.get(wf.phase, 0) + 1

    total_documents = len(documents_snap)

    # O(1) workflow lookup to find which projects have overdue approvals.
    wf_by_id = {wf.id: wf for wf in workflows_snap}
    projects_with_overdue: set[str] = set()
    for approval in approvals_snap:
        if approval.state == "overdue":
            wf = wf_by_id.get(approval.workflow)
            if wf and wf.project:
                projects_with_overdue.add(wf.project)

    now = datetime.now(timezone.utc)
    seven_days = now + timedelta(days=7)
    recently_created = 0
    for a in approvals_snap:
        if a.state == "pending" and a.deadline:
            # Use _to_aware_dt so already-aware deadline strings are handled
            # correctly — .replace(tzinfo=...) would discard existing tz info.
            deadline_dt = _to_aware_dt(a.deadline)
            if deadline_dt and now < deadline_dt < seven_days:
                recently_created += 1

    return {
        "generated_at": now.isoformat(),
        "projects": {
            "total": total_projects,
            "active": active_projects,
            "with_overdue_approvals": len(projects_with_overdue),
        },
        "approvals": {
            "total": total_approvals,
            "approved": approved_count,
            "pending": pending_count,
            "overdue": overdue_count,
            "approval_rate_pct": round(approval_rate, 1),
            "due_within_7_days": recently_created,
        },
        "documents": {
            "total": total_documents,
        },
        "phase_distribution": phase_distribution,
    }
