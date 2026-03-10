# SPDX-License-Identifier: MIT
"""Metrics recording and aggregation helpers."""

from __future__ import annotations

import re
from typing import Iterable, Mapping

from ..approvals import approvals
from ..documents import documents
from ..workflows import workflows
from ._models import AggregateStats, CriticAggregate

_DEFAULT_LATENCY_BUCKETS: tuple[str, ...] = ("<10ms", "10-50ms", "50-100ms", "100ms+")
_SANITIZE_RE = re.compile(r"[^a-z0-9]+")

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
