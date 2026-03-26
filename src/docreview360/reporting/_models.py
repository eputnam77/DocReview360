# SPDX-License-Identifier: MIT
"""Pydantic models and dataclasses for reporting."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ReviewerWorkload(BaseModel):
    """Per-reviewer metrics for the workload dashboard."""

    reviewer: str
    pending_approvals: int = 0
    approved_approvals: int = 0
    overdue_approvals: int = 0
    rejected_approvals: int = 0
    total_approvals: int = 0
    assigned_projects: int = 0


class DocumentAgingEntry(BaseModel):
    """Age summary for a single document."""

    document_id: str
    project: str | None = None
    age_days: int | None = None
    has_pending_approvals: bool = False
    has_overdue_approvals: bool = False


class DocumentAgingReport(BaseModel):
    """Aggregate aging metrics across all documents."""

    total_documents: int
    documents_with_known_age: int
    avg_age_days: float | None = None
    oldest_age_days: int | None = None
    documents_older_than_30_days: int = 0
    documents_older_than_90_days: int = 0
    entries: list[DocumentAgingEntry] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


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


class ThroughputEntry(BaseModel):
    """Daily approval counts used for throughput charts."""

    date: str
    approvals: int
