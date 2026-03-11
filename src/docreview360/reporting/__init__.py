# SPDX-License-Identifier: MIT
"""Reporting package — public re-exports.

All names previously importable from ``docreview360.reporting`` remain
available here for backward compatibility.
"""

from __future__ import annotations

from ._models import (
    AggregateStats,
    CriticAggregate,
    DashboardEntry,
    DocumentAgingEntry,
    DocumentAgingReport,
    ReviewerWorkload,
    SummaryReport,
    ThroughputEntry,
    WidgetMetrics,
)
from ._metrics import (
    record_quality_score,
    record_compliance_score,
    record_routing_snapshot,
    reset_metrics_for_testing,
)
from ._reports import (
    admin_dashboard,
    analytics_dashboard,
    analytics_export,
    avg_quality_score,
    compile_check_report,
    dashboard_data,
    doc_type_counts,
    document_aging_metrics,
    executive_summary,
    generate_summary,
    manager_dashboard,
    reviewer_workload_dashboard,
    summary_csv,
    throughput_csv,
    throughput_data,
    user_dashboard,
    widget_counts,
    workload_csv,
    workload_data,
)

__all__ = [
    # models
    "AggregateStats",
    "CriticAggregate",
    "DashboardEntry",
    "DocumentAgingEntry",
    "DocumentAgingReport",
    "ReviewerWorkload",
    "SummaryReport",
    "ThroughputEntry",
    "WidgetMetrics",
    # metrics
    "record_quality_score",
    "record_compliance_score",
    "record_routing_snapshot",
    "reset_metrics_for_testing",
    # reports
    "admin_dashboard",
    "analytics_dashboard",
    "analytics_export",
    "avg_quality_score",
    "compile_check_report",
    "dashboard_data",
    "doc_type_counts",
    "document_aging_metrics",
    "executive_summary",
    "generate_summary",
    "manager_dashboard",
    "reviewer_workload_dashboard",
    "summary_csv",
    "throughput_csv",
    "throughput_data",
    "user_dashboard",
    "widget_counts",
    "workload_csv",
    "workload_data",
]
