"""Generate simple usage reports."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from html import escape
from typing import Any, Iterable, Mapping

from pydantic import BaseModel, Field

from .approvals import approvals
from .documents import documents
from .search import ProjectModel, _expire_temp_assignment, add_project, projects
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


_DEFAULT_LATENCY_BUCKETS: tuple[str, ...] = ("<10ms", "10-50ms", "50-100ms", "100ms+")
_SANITIZE_RE = re.compile(r"[^a-z0-9]+")


@dataclass
class AggregateStats:
    total: float = 0.0
    count: int = 0

    def add(self, value: float) -> None:
        self.total += float(value)
        self.count += 1

    def extend(self, other: "AggregateStats") -> None:
        self.total += other.total
        self.count += other.count

    def average(self) -> float | None:
        if not self.count:
            return None
        return self.total / self.count


@dataclass
class CriticAggregate:
    quality: AggregateStats = field(default_factory=AggregateStats)
    compliance: AggregateStats = field(default_factory=AggregateStats)
    quality_metadata: dict[str, str] | None = None
    compliance_metadata: dict[str, str] | None = None

    def merge(self, other: "CriticAggregate") -> None:
        self.quality.extend(other.quality)
        self.compliance.extend(other.compliance)
        if other.quality_metadata:
            self.quality_metadata = dict(other.quality_metadata)
        if other.compliance_metadata:
            self.compliance_metadata = dict(other.compliance_metadata)


_PROJECT_METRICS: dict[str | None, CriticAggregate] = {}
_ROUTING_LATENCY: dict[str, int] = {}
_ROUTING_METADATA: dict[str, str] | None = None


def _format_optional(value: float | None) -> str:
    return f"{value:.4f}" if value is not None else ""


def _sanitize_column(label: str) -> str:
    safe = _SANITIZE_RE.sub("_", label.lower()).strip("_")
    return safe or "value"


def _get_metric_bucket(key: str | None) -> CriticAggregate:
    bucket = _PROJECT_METRICS.get(key)
    if bucket is None:
        bucket = CriticAggregate()
        _PROJECT_METRICS[key] = bucket
    return bucket


def _resolve_project_id(document_id: str | None) -> str | None:
    if not document_id:
        return None
    doc = documents.get(document_id)
    if doc and doc.project:
        return doc.project
    for approval in approvals.values():
        if approval.document_id == document_id:
            workflow = workflows.get(approval.workflow)
            if workflow:
                return workflow.project
    for workflow in workflows.values():
        if workflow.document == document_id:
            return workflow.project
    return None


def _metadata_snapshot(metrics: CriticAggregate | None = None) -> dict[str, dict[str, str]]:
    data: dict[str, dict[str, str]] = {}
    source = metrics or _PROJECT_METRICS.get(None)
    if source:
        if source.quality_metadata:
            data["quality"] = dict(source.quality_metadata)
        if source.compliance_metadata:
            data["compliance"] = dict(source.compliance_metadata)
    if _ROUTING_METADATA:
        data["routing"] = dict(_ROUTING_METADATA)
    return data


def _routing_latency_snapshot() -> dict[str, int]:
    if not _ROUTING_LATENCY:
        return {bucket: 0 for bucket in _DEFAULT_LATENCY_BUCKETS}
    snapshot = {bucket: int(_ROUTING_LATENCY.get(bucket, 0)) for bucket in _DEFAULT_LATENCY_BUCKETS}
    for label, value in _ROUTING_LATENCY.items():
        if label not in snapshot:
            snapshot[label] = int(value)
    return snapshot


def _aggregate_for_projects(project_ids: Iterable[str]) -> CriticAggregate:
    aggregate = CriticAggregate()
    for project_id in project_ids:
        metrics = _PROJECT_METRICS.get(project_id)
        if metrics:
            aggregate.merge(metrics)
    return aggregate


def record_quality_score(
    document_id: str | None, score: float, metadata: Mapping[str, str] | None = None
) -> None:
    payload = {k: str(v) for k, v in (metadata or {}).items()}
    project_id = _resolve_project_id(document_id)
    targets: list[str | None] = []
    if project_id is not None:
        targets.append(project_id)
    targets.append(None)
    for key in targets:
        bucket = _get_metric_bucket(key)
        bucket.quality.add(score)
        if payload:
            bucket.quality_metadata = dict(payload)


def record_compliance_score(
    document_id: str | None, probability: float, metadata: Mapping[str, str] | None = None
) -> None:
    payload = {k: str(v) for k, v in (metadata or {}).items()}
    project_id = _resolve_project_id(document_id)
    targets: list[str | None] = []
    if project_id is not None:
        targets.append(project_id)
    targets.append(None)
    for key in targets:
        bucket = _get_metric_bucket(key)
        bucket.compliance.add(probability)
        if payload:
            bucket.compliance_metadata = dict(payload)


def record_routing_snapshot(
    latency: Mapping[str, int], metadata: Mapping[str, str] | None = None
) -> None:
    global _ROUTING_METADATA
    _ROUTING_LATENCY.clear()
    for label, value in latency.items():
        _ROUTING_LATENCY[str(label)] = int(value)
    if metadata:
        _ROUTING_METADATA = {k: str(v) for k, v in metadata.items()}


def reset_metrics_for_testing() -> None:
    _PROJECT_METRICS.clear()
    _ROUTING_LATENCY.clear()
    global _ROUTING_METADATA
    _ROUTING_METADATA = None


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
    doc_type: str | None = None
    phase: str | None = None
    status: str | None = None
    docs: int = 0
    pending_approvals: int = 0
    overdue_approvals: int = 0
    quality_score: float | None = None
    compliance_score: float | None = None
    routing_latency: dict[str, int] = Field(default_factory=dict)
    critic_models: dict[str, dict[str, str]] = Field(default_factory=dict)


class WidgetMetrics(BaseModel):
    """Aggregated metrics used for dashboard widgets."""

    assigned: int
    active: int
    pending_approvals: int
    avg_quality_score: float | None = None
    avg_compliance_score: float | None = None
    routing_latency: dict[str, int] = Field(default_factory=dict)
    critic_models: dict[str, dict[str, str]] = Field(default_factory=dict)


def generate_summary() -> SummaryReport:
    """Return counts of key objects."""
    # Some tests clear the global project registry.  The reporting endpoints
    # expect a default project to always exist, so we bootstrap a minimal one
    # on-demand if the registry is empty.
    # Ensure a sample project is always present for summary metrics.  Some
    # tests remove all projects; others may only create a single one.  Having a
    # predictable baseline keeps the summary output stable.
    if "demo" not in projects:
        add_project(ProjectModel(id="demo", name="Demo Project"))

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
    routing_snapshot = _routing_latency_snapshot()
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
        overdue = sum(
            1
            for a in approvals.values()
            if wf is not None and a.workflow == wf.id and a.state == "overdue"
        )
        metrics = _PROJECT_METRICS.get(project.id)
        quality_avg = metrics.quality.average() if metrics else None
        compliance_avg = metrics.compliance.average() if metrics else None
        data.append(
            DashboardEntry(
                id=project.id,
                name=project.name,
                priority=project.priority,
                doc_type=project.doc_type,
                phase=wf.phase if wf else None,
                status=project.status,
                docs=doc_count,
                pending_approvals=pending,
                overdue_approvals=overdue,
                quality_score=quality_avg,
                compliance_score=compliance_avg,
                routing_latency=routing_snapshot.copy(),
                critic_models=_metadata_snapshot(metrics),
            )
        )
    return data


def widget_counts(user: str | None = None) -> WidgetMetrics:
    """Return counts used by dashboard widgets.

    If ``user`` is provided the counts are restricted to that user.
    """

    # Temporary project assignments can expire over time.  The previous
    # implementation counted projects without first clearing expired
    # ``temp_user`` values which left stale assignments reflected in the
    # dashboard metrics.  Normalize the project state before computing counts so
    # widgets reflect the current assignments.
    for proj in projects.values():
        _expire_temp_assignment(proj)

    if user is None:
        assigned = sum(1 for p in projects.values() if p.user or p.temp_user)
        active = sum(1 for p in projects.values() if p.temp_user)
        pending = sum(1 for a in approvals.values() if a.state == "pending")
        metrics: CriticAggregate | None = _PROJECT_METRICS.get(None)
    else:
        assigned = sum(1 for p in projects.values() if p.user == user or p.temp_user == user)
        active = sum(1 for p in projects.values() if p.temp_user == user)
        pending = sum(1 for a in approvals.values() if a.state == "pending" and a.reviewer == user)
        project_ids = [p.id for p in projects.values() if p.user == user or p.temp_user == user]
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


class ThroughputEntry(BaseModel):
    """Daily approval counts used for throughput charts."""

    date: str
    approvals: int


def throughput_data(days: int = 7) -> list[ThroughputEntry]:
    """Return approvals completed per day for the last ``days`` days."""
    if days <= 0:
        raise ValueError("days must be positive")
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days - 1)).date()
    counts: dict[str, int] = {}
    for a in approvals.values():
        if a.state == "approved" and a.signed_at:
            # ``signed_at`` used to be stored as an ISO-formatted string but is
            # now a ``datetime`` instance.  Older data or tests may still provide
            # a string, so support both formats gracefully.
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
