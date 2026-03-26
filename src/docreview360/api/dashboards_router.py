# SPDX-License-Identifier: MIT
"""Dashboards sub-router: /reports/*, /dashboard/*, /status/*, /metrics/*, /logs/*, /api/audit."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel

from .. import auth, reporting
from ..audit import humanize_audit_action
from ..config import CONFIG_FILE, Config
from ..dashboard_prefs import get_visibility, set_visibility
from ..logs import LogEntry, log_event, query_logs
from ..rbac import require_any_role, require_role, has_permission
from ..reporting import (
    DashboardEntry,
    DocumentAgingReport,
    ReviewerWorkload,
    SummaryReport,
    admin_dashboard,
    analytics_dashboard,
    analytics_export,
    dashboard_data,
    document_aging_metrics,
    executive_summary,
    generate_summary,
    manager_dashboard,
    reviewer_workload_dashboard,
    user_dashboard,
    WidgetMetrics,
    widget_counts,
)
from ..status import internal_status, public_status

_logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def require_audit_access(current_user: auth.User = Depends(auth.get_current_user)) -> str:
    """Ensure the requester may view audit logs and record the attempt."""
    if has_permission(current_user.username, "view_audit_log"):
        log_event("audit_log_access", user_id=current_user.username, status="success")
        return current_user.username
    log_event("audit_log_access", user_id=current_user.username, status="denied")
    raise HTTPException(status_code=403, detail="Forbidden")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class VisibilityPayload(BaseModel):
    """Dashboard widget visibility options."""

    stats: bool | None = None
    status: bool | None = None
    activity: bool | None = None
    logs: bool | None = None
    # Generic list of widget IDs chosen by the user (Item 45 Phase 3)
    widgets: list[str] | None = None


class EnrichedLogEntry(LogEntry):
    """LogEntry extended with a human-readable message for the dashboard feed."""

    human_message: str = ""


# ---------------------------------------------------------------------------
# Log routes
# ---------------------------------------------------------------------------

@router.get("/logs", response_model=list[LogEntry])
async def list_logs(
    start: datetime | None = None,
    end: datetime | None = None,
    user_id: str | None = None,
    entity_id: str | None = None,
    entity_type: str | None = None,
    action: str | None = None,
    severity: str | None = None,
    log_id: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
    _: str = Depends(require_audit_access),
) -> list[LogEntry]:
    """Return recorded logs with optional filters and pagination."""
    entries = query_logs(
        action=action,
        user_id=user_id,
        start=start,
        end=end,
        entity_id=entity_id,
        entity_type=entity_type,
        severity=severity,
        log_id=log_id,
        limit=limit,
        offset=offset,
    )
    if (cfg := Config.load(CONFIG_FILE)) and cfg.log_reads:
        log_event("audit_log_access", entity_id="logs", count=len(entries))
    return entries


@router.get("/api/audit", response_model=list[LogEntry])
async def list_audit(
    start: datetime | None = None,
    end: datetime | None = None,
    user_id: str | None = None,
    entity_id: str | None = None,
    entity_type: str | None = None,
    action: str | None = None,
    severity: str | None = None,
    log_id: str | None = None,
    page: int | None = None,
    size: int | None = None,
    limit: int | None = None,
    offset: int | None = None,
    _: str = Depends(require_audit_access),
) -> list[LogEntry]:
    """Alias for :func:`list_logs` used by the dashboard."""
    if page is not None:
        size = size or 50
        limit = size
        offset = page * size

    entries = query_logs(
        action=action,
        user_id=user_id,
        start=start,
        end=end,
        entity_id=entity_id,
        entity_type=entity_type,
        severity=severity,
        log_id=log_id,
        limit=limit,
        offset=offset,
    )
    if (cfg := Config.load(CONFIG_FILE)) and cfg.log_reads:
        log_event("audit_log_access", entity_id="logs", count=len(entries))
    return entries


@router.get("/dashboard/audit-feed", response_model=list[EnrichedLogEntry])
async def audit_feed(
    limit: int | None = 50,
    offset: int | None = None,
    _: str = Depends(require_audit_access),
) -> list[EnrichedLogEntry]:
    """Return recent audit events enriched with human-readable ``human_message`` descriptions.

    Intended for the admin dashboard activity feed.  Each entry includes the
    underlying ``LogEntry`` fields plus a plain-English ``human_message`` that
    explains who performed which action.
    """
    entries = query_logs(limit=limit, offset=offset)
    enriched: list[EnrichedLogEntry] = []
    for entry in entries:
        msg = humanize_audit_action(
            action=entry.action,
            user_id=entry.user_id,
            entity_id=entry.entity_id,
            details=entry.details,
        )
        enriched.append(EnrichedLogEntry(**entry.model_dump(), human_message=msg))
    return enriched


@router.get("/logs/export")
async def export_logs_endpoint(
    fmt: str = "json",
    start: datetime | None = None,
    end: datetime | None = None,
    user_id: str | None = None,
    entity_id: str | None = None,
    entity_type: str | None = None,
    action: str | None = None,
    severity: str | None = None,
    log_id: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
    _: str = Depends(require_audit_access),
) -> Response:
    filters = {
        k: v
        for k, v in {
            "start": str(start) if start else None,
            "end": str(end) if end else None,
            "user_id": user_id,
            "entity_id": entity_id,
            "entity_type": entity_type,
            "action": action,
            "severity": severity,
            "log_id": log_id,
            "limit": limit,
            "offset": offset,
        }.items()
        if v is not None
    }
    entries = query_logs(
        action=action,
        user_id=user_id,
        start=start,
        end=end,
        entity_id=entity_id,
        entity_type=entity_type,
        severity=severity,
        log_id=log_id,
        limit=limit,
        offset=offset,
    )
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filters": filters,
    }
    filter_str = ", ".join(f"{k}={v}" for k, v in filters.items()) or "none"
    header = "id,timestamp,user_id,action,entity_type,entity_id,severity,ip_address,details"
    rows = [
        f"{e.id},{e.timestamp},{e.user_id or ''},{e.action},{e.entity_type or ''},"
        f"{e.entity_id or ''},{e.severity},{e.ip_address or ''},{json.dumps(e.details)}"
        for e in entries
    ]
    if fmt == "csv":
        lines = [
            f"# Generated at: {metadata['generated_at']}",
            f"# Filters: {filter_str}",
            header,
            *rows,
        ]
        content = "\n".join(lines)
        media = "text/csv"
    elif fmt == "json":
        content = json.dumps(
            {"metadata": metadata, "logs": [e.model_dump(mode="json") for e in entries]}
        )
        media = "application/json"
    elif fmt == "pdf":
        lines = [
            f"Generated at: {metadata['generated_at']}",
            f"Filters: {filter_str}",
            "",
            header,
            *rows,
        ]
        content = b"%PDF-1.4\n" + "\n".join(lines).encode("utf-8")
        media = "application/pdf"
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")
    if (cfg := Config.load(CONFIG_FILE)) and cfg.log_reads:
        log_event("read", entity_id="logs_export", count=len(entries), fmt=fmt)
    return Response(content=content, media_type=media)


# ---------------------------------------------------------------------------
# Recently active users endpoint (Item 51)
# ---------------------------------------------------------------------------


class RecentlyActiveUser(BaseModel):
    """Summary of a recently active user for the admin dashboard."""

    username: str
    display_name: str
    roles: list[str]
    last_active: str | None = None
    action_count: int = 0


@router.get("/dashboard/recently-active-users", response_model=list[RecentlyActiveUser])
async def recently_active_users(
    days: int = 30,
    limit: int = 20,
    _user: auth.User = Depends(require_role("admin")),
) -> list[RecentlyActiveUser]:
    """Return users who have been active in the last ``days`` days.

    Each entry includes the actual username and display name — never just a
    role label — so the admin dashboard can show real people.
    """
    from datetime import timedelta

    from ..logs import query_logs

    since = datetime.now(timezone.utc) - timedelta(days=max(1, days))
    recent_logs = query_logs(start=since, limit=None)

    activity: dict[str, dict[str, Any]] = {}
    for entry in recent_logs:
        if not entry.user_id:
            continue
        username = entry.user_id
        if username not in activity:
            activity[username] = {"last_active": entry.timestamp, "count": 0}
        if entry.timestamp and (
            activity[username]["last_active"] is None
            or entry.timestamp > activity[username]["last_active"]
        ):
            activity[username]["last_active"] = entry.timestamp
        activity[username]["count"] += 1

    # Sort by action count descending, take top N
    ranked = sorted(activity.items(), key=lambda kv: kv[1]["count"], reverse=True)[:limit]

    try:
        from ..rbac import get_roles
        from ..profile import get_profile_data
    except ImportError:
        get_roles = lambda u: []  # noqa: E731
        get_profile_data = lambda u: {}  # noqa: E731

    result: list[RecentlyActiveUser] = []
    for username, info in ranked:
        roles = get_roles(username) if callable(get_roles) else []
        try:
            profile = get_profile_data(username) if callable(get_profile_data) else {}
            display_name = profile.get("displayName") or profile.get("name") or username
        except Exception:
            display_name = username
        last_ts = info["last_active"]
        result.append(
            RecentlyActiveUser(
                username=username,
                display_name=str(display_name),
                roles=sorted(roles),
                last_active=last_ts.isoformat() if last_ts else None,
                action_count=info["count"],
            )
        )
    return result


# ---------------------------------------------------------------------------
# Report routes
# ---------------------------------------------------------------------------

@router.get("/reports/summary", response_model=SummaryReport)
async def get_summary_report(
    current_user: auth.User = Depends(auth.get_current_user),
) -> SummaryReport:
    """Return counts of projects, documents, workflows, and approvals."""
    return generate_summary()


@router.get("/metrics/summary", response_model=SummaryReport)
async def get_metrics_summary(
    current_user: auth.User = Depends(auth.get_current_user),
) -> SummaryReport:
    """Alias for :func:`get_summary_report` used by dashboards."""
    return generate_summary()


@router.get("/reports/summary.csv")
async def get_summary_csv(
    current_user: auth.User = Depends(auth.get_current_user),
) -> Response:
    """Return the summary report as CSV."""
    return Response(reporting.summary_csv(), media_type="text/csv")


@router.get("/reports/throughput", response_model=list[reporting.ThroughputEntry])
async def throughput_endpoint(
    days: int = 7,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[reporting.ThroughputEntry]:
    """Return approval throughput data."""
    return reporting.throughput_data(days)


@router.get("/reports/throughput.csv")
async def throughput_csv_endpoint(
    days: int = 7,
    current_user: auth.User = Depends(auth.get_current_user),
) -> Response:
    """CSV export of :func:`throughput_endpoint`."""
    return Response(reporting.throughput_csv(days), media_type="text/csv")


@router.get("/reports/workload", response_model=dict[str, int])
async def workload_endpoint(
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, int]:
    """Return workload counts per user."""
    return reporting.workload_data()


@router.get("/reports/workload.csv")
async def workload_csv_endpoint(
    current_user: auth.User = Depends(auth.get_current_user),
) -> Response:
    """CSV export of :func:`workload_endpoint`."""
    return Response(reporting.workload_csv(), media_type="text/csv")


@router.get("/reports/dashboard", response_model=list[DashboardEntry])
async def get_dashboard_data(
    x_user: str | None = Header(None),
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[DashboardEntry]:
    """Return per-project data for dashboard widgets."""
    return dashboard_data(x_user)


@router.get("/reports/document-aging", response_model=DocumentAgingReport)
async def document_aging_endpoint(
    current_user: auth.User = Depends(auth.get_current_user),
) -> DocumentAgingReport:
    """Return document aging metrics across all documents."""
    return document_aging_metrics()


# ---------------------------------------------------------------------------
# Dashboard routes
# ---------------------------------------------------------------------------

@router.get("/dashboard/user")
async def user_dashboard_endpoint(
    x_user: str | None = Header(None),
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Return dashboard data for the authenticated user, including quality KPI."""
    effective_user = x_user or current_user.username
    return user_dashboard(effective_user)


@router.get("/dashboard/widgets", response_model=WidgetMetrics)
async def get_widget_counts(
    x_user: str | None = Header(None),
    current_user: auth.User = Depends(auth.get_current_user),
) -> WidgetMetrics:
    """Return assignment and approval counts for dashboard widgets."""
    return widget_counts(x_user or current_user.username)


@router.get("/dashboard/doc-types", response_model=dict[str, int])
async def doc_type_counts_endpoint(
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, int]:
    """Return active project counts grouped by document type."""
    return reporting.doc_type_counts()


@router.get("/dashboard/visibility")
async def get_visibility_endpoint(
    x_user: str | None = Header(None),
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Return saved visibility settings for the user.

    The response includes legacy boolean fields (``stats``, ``status``,
    ``activity``, ``logs``) plus a ``widgets`` list of visible widget IDs.
    """
    effective_user = x_user or current_user.username
    return get_visibility(effective_user)


@router.put("/dashboard/visibility")
async def update_visibility_endpoint(
    body: VisibilityPayload,
    x_user: str | None = Header(None),
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Persist user visibility preferences.

    Accepts legacy boolean fields and/or a ``widgets`` list of widget IDs.
    Returns the merged result including both the boolean flags and the
    ``widgets`` list.
    """
    effective_user = x_user or current_user.username
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    return set_visibility(effective_user, data)


@router.get("/dashboard/manager")
async def manager_dashboard_endpoint(
    user: auth.User = Depends(require_role("manager")),
) -> dict[str, Any]:
    """Return dashboard information for managers."""
    return manager_dashboard()


@router.get("/dashboard/admin")
async def admin_dashboard_endpoint(
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Return system overview for administrators."""
    return admin_dashboard()


@router.get("/dashboard/executive-summary", response_model=dict[str, Any])
async def executive_summary_endpoint(
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Return a high-level portfolio summary for leadership."""
    return executive_summary()


@router.get("/dashboard/reviewer-workload", response_model=list[ReviewerWorkload])
async def reviewer_workload_endpoint(
    user: auth.User = Depends(require_role("admin")),
) -> list[ReviewerWorkload]:
    """Return per-reviewer workload metrics."""
    return reviewer_workload_dashboard()


@router.get("/dashboard/analytics")
async def analytics_dashboard_endpoint(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    user: auth.User = Depends(require_any_role("manager", "admin")),
) -> dict[str, Any]:
    """Return comprehensive analytics data.

    Requires manager or admin role.  Returns document stats, review stats,
    user activity, quality trends, and phase throughput.
    """
    return analytics_dashboard(start_date=start_date, end_date=end_date)


@router.get("/reports/analytics/export")
async def analytics_export_endpoint(
    format: str = "json",
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    user: auth.User = Depends(require_role("admin")),
) -> Response:
    """Export analytics report as JSON or CSV.

    Query params:
      - ``format``: ``json`` (default) or ``csv``
      - ``start_date``, ``end_date``: ISO-8601 date/time range filter
    """
    if format not in {"json", "csv"}:
        raise HTTPException(status_code=400, detail="Unsupported format; use 'json' or 'csv'")
    content, media_type = analytics_export(
        fmt=format, start_date=start_date, end_date=end_date
    )
    return Response(content=content, media_type=media_type)


# ---------------------------------------------------------------------------
# Status routes
# ---------------------------------------------------------------------------

@router.get("/status/public")
async def public_status_endpoint() -> dict[str, int]:
    """Expose limited status for unauthenticated users."""
    return public_status()


@router.get("/status/internal")
async def internal_status_endpoint(
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, int]:
    """Return extended system status for authenticated users."""
    return internal_status()
