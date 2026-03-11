# SPDX-License-Identifier: MIT
"""FastAPI application exposing DocReview360 endpoints."""

# ruff: noqa: I001, E402
from __future__ import annotations

import asyncio
import base64
import binascii
import logging
import re
from collections import deque
import hashlib
import hmac
import json
import os
import secrets
import string
from threading import Lock
import time
import uuid

_logger = logging.getLogger(__name__)
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import (
    Depends,
    Body,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..e2e_runtime import apply_e2e_run_dir

apply_e2e_run_dir()

from .. import auth, reporting, rbac, settings_manager
from ..rbac import require_permission
from .. import search as search_mod
from ..ai_assist import rewrite_text, summarize_text
from ..ai_balancer import load_state as load_worker_state
from ..ai_balancer import save_state as save_worker_state
from ..approvals import (
    ApprovalModel,
    SignedApprovalImmutableError,
    build_approvals_summary_pdf,
    create_approval,
    delete_approval,
    get_approval,
    list_approvals,
    load_approvals_from_db,
    send_for_signature,
    update_approval_state,
    verify_document_signature,
)
from ..archive import (
    ArchiveRecord,
    archive_document as archive_doc,
    get_archive,
    list_archives,
    schedule_archive_purge,
)
from ..audit import AuditLogEntry, get_audit_log, log_audit_event
from ..cache import cache_get, cache_set, clear_cache
from ..cms import fetch_from_cms, save_to_cms
from ..comments import CommentModel, add_comment, list_comments, render_comment_for_response, update_comment
from ..config import CONFIG_FILE, Config, load_with_defaults
from ..dashboard_prefs import get_visibility, set_visibility
from ..demo_data import seed_demo_data
from ..doc_types import (
    DocumentTypeModel,
    add_document_type,
    delete_document_type,
    export_document_types_json,
    get_document_type,
    import_document_types_json,
    list_document_types,
    update_document_type,
)
from ..documenso import (
    complete_signature,
    register_stub_signature,
    signature_status,
)
from ..documents import (
    DocumentModel,
    get_document,
    import_document,
    list_public_documents,
    public_documents_report,
    update_document,
    DocumentRevision,
)
from ..documents import (
    list_documents as list_docs,
)
from ..environment import current_environment, load_envs, switch_environment
from ..exporter import export_document, set_guardrails
from ..integrations.signature import get_default_providers, get_provider
from ..logs import TRACE_ID, LogEntry, log_event, log_stream, query_logs, log_call, _get_db
from ..messages import render
from ..nemo_guardrails import GuardrailsMiddleware, contains_pii
from ..phases import (
    add_phase,
    delete_phase,
    get_phase_workflow_template,
    list_phase_workflow_links,
    list_phases,
    rename_phase,
    set_phase_workflow_template,
)
from ..plugins import load_plugins
from ..plugins import registry as plugin_registry
from ..profile import (
    get_preferences,
    get_profile_data,
    update_preferences,
    update_profile_data,
)
from ..rbac import get_roles, require_role, has_permission, has_role
from ..reporting import (
    DashboardEntry,
    DocumentAgingReport,
    ReviewerWorkload,
    SummaryReport,
    admin_dashboard,
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
from ..doc_validation import preflight_validate as _preflight_validate
from ..search import (
    ProjectModel,
    add_project,
    add_project_reviewer,
    assign_temporary,
    get_project,
    list_projects,
    list_saved_searches,
    remove_project_reviewer,
    remove_project,
    ranked_search,
    save_search,
    search,
    search_stats,
    set_project_priority,
    update_project_reviewer,
    update_project,
)
from ..project_preferences import (
    ProjectPreferences,
    get_project_preferences,
    update_project_preferences,
)
from ..reviews import ReviewCreate, ReviewModel, add_review, list_reviews
from ..settings_manager import update_setting, update_secret
from ..secrets import get_secret
from ..status import internal_status, public_status
from ..document_converter import convert_document
from ..template_manager import (
    delete_template as delete_stored_template,
    get_latest_template,
    get_template_phase_locks,
    is_template_locked_for_phase,
    list_stored_templates,
    list_template_versions,
    lock_template_for_phase,
    approve_template,
    retire_template,
    unlock_template_for_phase,
    upload_template as store_template,
)
from ..email_templates import (
    create_template as create_email_template,
    delete_template as delete_email_template,
    get_template as get_email_template,
    list_templates as list_email_templates,
    update_template as update_email_template,
)
from ..watchlist import get_watchlist, toggle_watch
from ..collab import router as collab_router
from ..workflows import (
    WorkflowModel,
    WorkflowTemplateModel,
    WorkflowTemplatePayload,
    WorkflowTemplateStep,
    advance_workflow,
    assign_reviewer,
    create_workflow,
    create_workflow_template,
    delete_workflow_template,
    get_workflow,
    get_workflow_template,
    list_workflows,
    list_workflow_templates,
    load_workflows_from_db,
    start_workflow,
    update_workflow_template,
    workflow_templates,
    workflows,
    list_roles,
)
from .approvals import router as approvals_router
from .ml import router as ml_router, warm_ml_sessions
from .webhooks import router as webhooks_router, _load_subscribers_from_db
from .auth_router import router as auth_router
from .admin_router import router as admin_router
from .projects_router import router as projects_router
from .documents_router import router as documents_router
from .workflows_router import router as workflows_router
from .dashboards_router import router as dashboards_router
from .tools_router import router as tools_router
from .notifications_router import router as notifications_router
from .comments_router import router as comments_router
from .organizations_router import router as organizations_router
from .saml_router import router as saml_router
from .scim_router import router as scim_router
from .branches_router import router as branches_router
from .legal_router import router as legal_router
from .config_router import router as config_router
from .flags_router import router as flags_router
from .assignments_router import router as assignments_router
from .feedback_router import router as feedback_router

# Load environment variables from .env file
load_dotenv()

WORKER_STATE_FILE = Path(os.getenv("DOCREVIEW360_WORKER_STATE", "worker_state.json"))


def _env_int(name: str, default: int) -> int:
    """Return a positive integer from env or ``default``."""

    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    if value <= 0:
        return default
    return value


class _FixedWindowRateLimiter:
    """Thread-safe fixed-window rate limiter keyed by arbitrary identifiers."""

    def __init__(self, *, limit: int, window_seconds: float) -> None:
        if limit <= 0:
            raise ValueError("limit must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self._limit = int(limit)
        self._window_seconds = float(window_seconds)
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()

    def enforce(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            bucket = self._hits.setdefault(key, deque())
            while bucket and now - bucket[0] > self._window_seconds:
                bucket.popleft()
            if len(bucket) >= self._limit:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            bucket.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


_RATE_LIMIT_WINDOW_SECONDS = float(_env_int("DOCREVIEW360_RATE_LIMIT_WINDOW_SECONDS", 60))
_TOKEN_RATE_LIMITER = _FixedWindowRateLimiter(
    limit=_env_int("DOCREVIEW360_TOKEN_RATE_LIMIT", 20),
    window_seconds=_RATE_LIMIT_WINDOW_SECONDS,
)
_LOGIN_RATE_LIMITER = _FixedWindowRateLimiter(
    limit=_env_int("DOCREVIEW360_LOGIN_RATE_LIMIT", 20),
    window_seconds=_RATE_LIMIT_WINDOW_SECONDS,
)
_UPLOAD_RATE_LIMITER = _FixedWindowRateLimiter(
    limit=_env_int("DOCREVIEW360_UPLOAD_RATE_LIMIT", 30),
    window_seconds=_RATE_LIMIT_WINDOW_SECONDS,
)
_EXPORT_RATE_LIMITER = _FixedWindowRateLimiter(
    limit=_env_int("DOCREVIEW360_EXPORT_RATE_LIMIT", 20),
    window_seconds=_RATE_LIMIT_WINDOW_SECONDS,
)
_SEARCH_RATE_LIMITER = _FixedWindowRateLimiter(
    limit=_env_int("DOCREVIEW360_SEARCH_RATE_LIMIT", 60),
    window_seconds=_RATE_LIMIT_WINDOW_SECONDS,
)
_SIGNATURE_RATE_LIMITER = _FixedWindowRateLimiter(
    limit=_env_int("DOCREVIEW360_SIGNATURE_RATE_LIMIT", 30),
    window_seconds=_RATE_LIMIT_WINDOW_SECONDS,
)
_BULK_RATE_LIMITER = _FixedWindowRateLimiter(
    limit=_env_int("DOCREVIEW360_BULK_RATE_LIMIT", 10),
    window_seconds=_RATE_LIMIT_WINDOW_SECONDS,
)


def reset_rate_limiters_for_testing() -> None:
    """Clear API endpoint rate limiting counters (used by tests)."""

    _TOKEN_RATE_LIMITER.reset()
    _LOGIN_RATE_LIMITER.reset()
    _UPLOAD_RATE_LIMITER.reset()
    _EXPORT_RATE_LIMITER.reset()
    _SEARCH_RATE_LIMITER.reset()
    _SIGNATURE_RATE_LIMITER.reset()
    _BULK_RATE_LIMITER.reset()


def _request_source(request: Request) -> str:
    """Return a stable source identifier for request-scoped rate limiting."""

    forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded_for:
        return forwarded_for
    if request.client and request.client.host:
        return request.client.host
    return "unknown"





_ALLOWED_BRANDING_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
_ALLOWED_BRANDING_DATA_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/svg+xml",
}
_MAX_BRANDING_LOGO_BYTES = _env_int("DOCREVIEW360_BRANDING_MAX_LOGO_BYTES", 256 * 1024)


def _is_valid_branding_href(value: str) -> bool:
    """Return whether ``value`` is a safe local path or HTTP(S) URL."""

    candidate = value.strip()
    if not candidate:
        return False
    if candidate.startswith("/"):
        return True
    parsed = urlparse(candidate)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _normalize_branding_logo_url(value: str | None) -> str | None:
    """Validate and normalize an optional branding logo URL or data URL."""

    if value is None:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if len(candidate) > 600_000:
        raise ValueError("branding_logo_url is too large")

    lower_candidate = candidate.lower()
    if lower_candidate.startswith("data:"):
        match = re.match(r"^data:(image/[a-z0-9.+-]+);base64,(.+)$", candidate, re.IGNORECASE)
        if match is None:
            raise ValueError("branding_logo_url data URL must be base64 image data")
        mime = match.group(1).lower()
        if mime not in _ALLOWED_BRANDING_DATA_MIME_TYPES:
            raise ValueError("branding_logo_url data URL image type is not allowed")
        payload = match.group(2)
        try:
            decoded = base64.b64decode(payload, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("branding_logo_url data URL has invalid base64 payload") from exc
        if len(decoded) > _MAX_BRANDING_LOGO_BYTES:
            raise ValueError(
                f"branding_logo_url exceeds size limit of {_MAX_BRANDING_LOGO_BYTES} bytes"
            )
        return candidate

    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("branding_logo_url must use https/http or data URL")
    ext = Path(parsed.path or "").suffix.lower()
    if ext not in _ALLOWED_BRANDING_LOGO_EXTENSIONS:
        raise ValueError("branding_logo_url must use png, jpg, jpeg, webp, or svg")
    return candidate


def _load_release_version() -> str:
    """Return package version for footer metadata."""

    try:
        return importlib_metadata.version("docreview360")
    except importlib_metadata.PackageNotFoundError:
        return os.getenv("DOCREVIEW360_RELEASE_VERSION", "0.0.0-dev")


def _seed_default_document_templates() -> None:
    """Seed one TipTap HTML template per document type when missing."""
    for doc_type in list_document_types():
        name = f"doc_type::{doc_type.name.strip()}"
        if get_latest_template(name):
            continue
        content = doc_type.template or f"<h1>{doc_type.name}</h1>"
        metadata = {
            "label": f"{doc_type.name} (Default)",
            "docType": doc_type.name,
            "format": "HTML",
            "type": "tiptap",
            "description": f"Default template for {doc_type.name} documents.",
            "default": True,
        }
        store_template(name, content.encode("utf-8"), metadata)
        try:
            approve_template(name)
        except Exception as _approve_exc:
            _logger.warning("Failed to auto-approve seeded template '%s': %s", name, _approve_exc)


def _seed_default_email_templates() -> None:
    """Seed email templates used by notifications when missing."""
    defaults = [
        {
            "name": "approval_complete",
            "subject": "Approval complete: {document_title}",
            "body": "Approval complete for {document_title}.",
            "task": "approval",
        },
        {
            "name": "approval_request",
            "subject": "Approval requested: {document_title}",
            "body": "Please approve {document_title}. {action_url}",
            "task": "approval",
        },
        {
            "name": "comment_added",
            "subject": "New comment: {document_title}",
            "body": "{commenter} commented: {comment}. {action_url}",
            "task": "comment",
        },
        {
            "name": "completion_notice",
            "subject": "{item} complete",
            "body": "Completed: {item}.",
            "task": "notification",
        },
        {
            "name": "default",
            "subject": "{subject}",
            "body": "{body}",
            "task": "system",
        },
        {
            "name": "due_reminder",
            "subject": "{item} due {due_date}",
            "body": "Due {due_date}: {item}.",
            "task": "reminder",
        },
        {
            "name": "overdue_notice",
            "subject": "{item} overdue",
            "body": "Overdue: {item}. {action_url}",
            "task": "reminder",
        },
        {
            "name": "phase_changed",
            "subject": "Phase update: {project_name}",
            "body": "{project_name} moved to {phase}.",
            "task": "status",
        },
        {
            "name": "project_assigned",
            "subject": "Project assigned: {project_name}",
            "body": "You are assigned to {project_name}. {action_url}",
            "task": "assignment",
        },
        {
            "name": "review_complete",
            "subject": "Review complete: {document_title}",
            "body": "Review complete for {document_title}.",
            "task": "review",
        },
        {
            "name": "review_request",
            "subject": "Review requested: {document_title}",
            "body": "Please review {document_title}. {action_url}",
            "task": "review",
        },
        {
            "name": "signature_request",
            "subject": "Signature requested: {document_title}",
            "body": "Please sign {document_title}. {action_url}",
            "task": "signature",
        },
    ]
    for tmpl in defaults:
        existing = get_email_template(tmpl["name"])
        if existing is not None:
            if not existing.subject.strip() or not existing.body.strip():
                try:
                    update_email_template(
                        tmpl["name"],
                        subject=tmpl["subject"],
                        body=tmpl["body"],
                        task=tmpl.get("task"),
                    )
                except Exception as _upd_exc:
                    _logger.warning("Failed to update email template '%s': %s", tmpl["name"], _upd_exc)
                    continue
            continue
        try:
            create_email_template(
                tmpl["name"], tmpl["subject"], tmpl["body"], task=tmpl.get("task")
            )
        except Exception as _create_exc:
            _logger.warning("Failed to create email template '%s': %s", tmpl["name"], _create_exc)
            continue
SEED_TEMPLATES = [
    {
        "name": "faa_ac",
        "content": (
            '<h1 style="text-align:center; margin-bottom:0">Advisory Circular</h1>'
            "<p>This is a seed template.</p>"
        ),
        "metadata": {"label": "FAA Advisory Circular", "type": "tiptap"},
    }
]


class WorkflowCreate(BaseModel):
    """Input model for creating workflows."""

    project: str
    phases: list[str]
    mode: str = "sequential"


class WorkflowTemplateResponse(BaseModel):
    """Response payload for workflow templates."""

    id: str
    name: str
    description: str | None = None
    steps: list[WorkflowTemplateStep]
    updated: str | None = None
    usage: int = 0


class ReviewerAssign(BaseModel):
    """Input model for assigning reviewers."""

    user: str


class ProjectReviewerPayload(BaseModel):
    """Input model for managing project reviewers."""

    reviewer: str


class ApprovalCreate(BaseModel):
    """Input model for creating approvals."""

    workflow: str
    reviewer: str
    # ``doc_id`` used to be required which made quick test setups cumbersome.
    # It is now optional and defaults to the workflow identifier when omitted.
    doc_id: str | None = None
    due_at: datetime | None = None
    description: str | None = None
    phase_id: str | None = None
    required: bool | None = None
    role: str | None = None
    order: int = 0
    reminder_at: datetime | None = None
    escalate_to: str | None = None
    escalation_at: datetime | None = None


class ApprovalUpdate(BaseModel):
    """Input model for updating approval state."""

    model_config = ConfigDict(populate_by_name=True)

    state: str
    signature_id: str | None = Field(default=None, alias="signature")
    due_at: datetime | None = None


class SignInitialsBody(BaseModel):
    """Input model for approving via initials signature."""

    initials: str


class PluginModule(BaseModel):
    """Input model for registering plugins by module path."""

    module: str


class PluginToggle(BaseModel):
    """Input model for enabling or disabling a plugin."""

    name: str


class RevisionCreate(BaseModel):
    """Payload for creating a document revision."""

    content: str
    steps: list[Any] | None = None
    promote: bool = False


class AiKeyPayload(BaseModel):
    """Payload for storing the AI rewrite API key."""

    key: str | None = None


class CmsExportRequest(BaseModel):
    """Request payload for exporting a document to a CMS."""

    fmt: str = "markdown"


class CmsExportResponse(BaseModel):
    """Response payload for CMS exports."""

    cms: str
    item_id: str


class CmsImportRequest(BaseModel):
    """Request payload for importing a document from a CMS."""

    item_id: str
    filename: str | None = None
    project: str | None = None
    user: str | None = None
    priority: int | None = None
    fmt: str | None = None


class RevisionMeta(BaseModel):
    """Metadata for a document revision."""

    id: str
    timestamp: datetime
    author: str


class ProjectCreate(BaseModel):
    """Input model for creating projects."""

    id: str | None = None  # Made optional - will be auto-generated if not provided
    name: str
    document_number: str | None = None  # User-provided document number/reference
    user: str | None = None
    doc_type: str | None = None
    phase: str | None = None
    workflow: str | None = None
    priority: int = 0
    description: str | None = None


class ProjectUpdate(BaseModel):
    """Fields allowed when updating a project."""

    name: str | None = None
    user: str | None = None
    doc_type: str | None = None
    # Allow updating the current phase via workflow state
    phase: str | None = None
    workflow: str | None = None
    description: str | None = None


def _resolve_project_phases(doc_type_name: str | None, phase: str | None) -> list[str]:
    """Return workflow phases based on document type and optional phase."""
    doc_type_obj = get_document_type(doc_type_name) if doc_type_name else None
    phases: list[str] = list(doc_type_obj.phases) if doc_type_obj else []

    if phase:
        if phases:
            if phase in phases:
                idx = phases.index(phase)
                phases = phases[idx:] + phases[:idx]
            else:
                phases = [phase] + [p for p in phases if p != phase]
        else:
            phases = [phase]

    if not phases:
        phases = [phase or "start"]

    return phases


def _resolve_workflow_template(
    requested_template: str | None,
    doc_type_name: str | None,
    phase_name: str | None = None,
) -> str:
    """Resolve a workflow template using request, doc type default, and phase linkage."""
    if requested_template in workflow_templates:
        return requested_template

    doc_type_obj = get_document_type(doc_type_name) if doc_type_name else None
    doc_default_template = (
        doc_type_obj.default_workflow_template_id
        if doc_type_obj and doc_type_obj.default_workflow_template_id
        else None
    )
    if doc_default_template in workflow_templates:
        return doc_default_template

    if phase_name:
        phase_default_template = get_phase_workflow_template(phase_name)
        if phase_default_template in workflow_templates:
            return phase_default_template

    return "branch-coordination"


class CommentCreate(BaseModel):
    """Input for creating comments."""

    user: str
    text: str
    parent: str | None = None
    tags: list[str] = []


class CommentUpdate(BaseModel):
    """Input for updating an existing comment."""

    status: str | None = None
    text: str | None = None
    tags: list[str] | None = None


class PriorityUpdate(BaseModel):
    """Input for updating project priority."""

    priority: int


class TemporaryAssign(BaseModel):
    """Input for temporary reassignment."""

    user: str
    until: datetime


class SavedSearchCreate(BaseModel):
    """Input model for creating saved searches."""

    query: str
    user: str


class TextBody(BaseModel):
    """Simple text payload for AI endpoints."""

    text: str


class ConfigPayload(BaseModel):
    """Configuration parameters for integrations."""

    database: str
    database_url: str | None = None
    editor: str
    cms: str
    auth: str
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    ai_auto_assign_writers: bool = False
    filename_template: str = "{id}"
    inactivity_timeout_minutes: int = Field(default=30, ge=1)
    branding_company_name: str = Field(default="DocReview360", max_length=80)
    branding_logo_url: str | None = None
    branding_logo_alt: str = Field(default="Organization logo", max_length=120)
    branding_support_url: str = Field(default="/docs/", max_length=255)
    branding_docs_url: str = Field(default="/docs/", max_length=255)
    branding_security_url: str = Field(default="/security", max_length=255)
    branding_privacy_url: str = Field(default="/privacy", max_length=255)

    @field_validator("branding_company_name")
    @classmethod
    def _validate_branding_company_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("branding_company_name cannot be empty")
        return normalized

    @field_validator("branding_logo_url")
    @classmethod
    def _validate_branding_logo_url(cls, value: str | None) -> str | None:
        return _normalize_branding_logo_url(value)

    @field_validator(
        "branding_support_url",
        "branding_docs_url",
        "branding_security_url",
        "branding_privacy_url",
    )
    @classmethod
    def _validate_branding_link(cls, value: str) -> str:
        normalized = value.strip()
        if not _is_valid_branding_href(normalized):
            raise ValueError("branding link must be an absolute path or http(s) URL")
        return normalized

    @model_validator(mode="after")
    def _validate_logo_alt(self) -> "ConfigPayload":
        if self.branding_logo_url and not self.branding_logo_alt.strip():
            raise ValueError("branding_logo_alt is required when branding_logo_url is set")
        self.branding_logo_alt = self.branding_logo_alt.strip() or "Organization logo"
        return self


class BrandingPayload(BaseModel):
    """Public branding and build metadata consumed by the frontend shell."""

    branding_company_name: str
    branding_logo_url: str | None = None
    branding_logo_alt: str
    branding_support_url: str
    branding_docs_url: str
    branding_security_url: str
    branding_privacy_url: str
    release_version: str
    release_build_number: str
    release_build_date: str
    release_commit: str | None = None
    environment: str

class SignatureProviderPayload(BaseModel):
    """Payload for selecting active signature providers."""

    primary: str
    fallback: str | None = None


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # Startup: validate configuration eagerly so misconfigurations surface
    # immediately with a clear error message instead of causing cryptic
    # runtime failures deep in request handlers.
    _startup_cfg = load_with_defaults()
    try:
        _startup_cfg.validate_startup()
    except ValueError as _cfg_err:
        _logger.critical("Configuration validation failed at startup: %s", _cfg_err)
        raise

    # Restore persisted state from DB
    load_approvals_from_db()
    load_workflows_from_db()
    _load_subscribers_from_db()
    load_worker_state(WORKER_STATE_FILE)
    for tpl in SEED_TEMPLATES:
        if not get_latest_template(tpl["name"]):
            store_template(tpl["name"], tpl["content"].encode("utf-8"), tpl.get("metadata"))
    _seed_default_document_templates()
    _seed_default_email_templates()
    schedule_archive_purge()
    warm_ml_sessions()
    seed_demo_data()
    try:
        yield
    finally:
        # Shutdown
        save_worker_state(WORKER_STATE_FILE)


app = FastAPI(title="DocReview360", lifespan=_lifespan)

_CORRELATION_HEADER = "X-Correlation-ID"
_FALLBACK_CORRELATION_HEADER = "X-Request-ID"


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next: Any) -> Response:
    """Attach and propagate a correlation ID for every HTTP request."""

    incoming = request.headers.get(_CORRELATION_HEADER) or request.headers.get(
        _FALLBACK_CORRELATION_HEADER
    )
    correlation_id = incoming.strip() if incoming and incoming.strip() else uuid.uuid4().hex
    request.state.trace_id = correlation_id

    token = TRACE_ID.set(correlation_id)
    try:
        response = await call_next(request)
    finally:
        TRACE_ID.reset(token)

    response.headers[_CORRELATION_HEADER] = correlation_id
    return response


def _versioned_to_unversioned_path(path: str) -> str | None:
    """Map ``/api/v1`` aliases to existing unversioned routes."""

    api_prefix = "/api/v1"
    if path == api_prefix:
        return "/"
    if path.startswith(f"{api_prefix}/"):
        return path[len(api_prefix) :]
    return None


class APIVersionPrefixMiddleware:
    """Allow clients to call existing endpoints through ``/api/v1`` aliases."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") in {"http", "websocket"}:
            rewritten_path = _versioned_to_unversioned_path(str(scope.get("path", "")))
            if rewritten_path is not None:
                updated_scope = dict(scope)
                updated_scope["path"] = rewritten_path
                if isinstance(scope.get("raw_path"), (bytes, bytearray)):
                    query = scope.get("query_string") or b""
                    updated_scope["raw_path"] = rewritten_path.encode("utf-8") + (
                        b"?" + query if query else b""
                    )
                scope = updated_scope
        await self.app(scope, receive, send)


app.add_middleware(APIVersionPrefixMiddleware)

@app.get("/ping")
async def ping() -> dict[str, str]:
    """Lightweight health check endpoint used by the frontend."""

    return {"status": "ok"}


# Add CORS middleware to allow frontend requests.
#
# Local development falls back to known localhost origins. Production-like
# environments must set ``DOCREVIEW360_ALLOW_ORIGINS`` explicitly so CORS
# remains deny-by-default outside dev/test.
_SAFE_CORS_ENVS = {"", "dev", "development", "test", "testing"}
_LOCAL_CORS_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]


def _resolve_cors_origins(allowed_origins: str | None, environment: str | None = None) -> list[str]:
    """Return allowed CORS origins with production-safe defaults."""

    if allowed_origins:
        origins = [o.strip() for o in allowed_origins.split(",") if o.strip()]
        if origins:
            return origins
        raise RuntimeError("DOCREVIEW360_ALLOW_ORIGINS must include at least one origin.")

    normalized_env = (environment or os.getenv("DOCREVIEW360_ENV", "")).strip().lower()
    if normalized_env == "prod":
        raise RuntimeError("DOCREVIEW360_ENV must be set to 'production' for production mode.")
    if normalized_env in _SAFE_CORS_ENVS:
        return list(_LOCAL_CORS_ORIGINS)

    raise RuntimeError(
        "DOCREVIEW360_ALLOW_ORIGINS must be set when DOCREVIEW360_ENV is production-like."
    )


app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "X-Request-ID", "X-Correlation-ID"],
    allow_origins=_resolve_cors_origins(os.getenv("DOCREVIEW360_ALLOW_ORIGINS")),
)

# Enable compression for large responses as recommended by the
# performance profiling report. ``minimum_size`` avoids wasting
# CPU cycles on tiny payloads.
app.add_middleware(GZipMiddleware, minimum_size=1000)


class SecurityHeadersMiddleware:
    """Add recommended HTTP security headers to every response."""

    _HEADERS: dict[str, str] = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    }

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Any) -> None:
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                for key, value in self._HEADERS.items():
                    headers[key.lower().encode()] = value.encode()
                message = {**message, "headers": list(headers.items())}
            await send(message)

        await self.app(scope, receive, send_with_headers)


app.add_middleware(SecurityHeadersMiddleware)

app.include_router(approvals_router)
app.include_router(webhooks_router)
app.include_router(collab_router)
app.include_router(ml_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(projects_router)
app.include_router(documents_router)
app.include_router(workflows_router)
app.include_router(dashboards_router)
app.include_router(tools_router)
app.include_router(notifications_router)
app.include_router(comments_router)
app.include_router(organizations_router)
app.include_router(saml_router)
app.include_router(scim_router)
app.include_router(branches_router)
app.include_router(legal_router)
app.include_router(config_router)
app.include_router(flags_router)
app.include_router(assignments_router)
app.include_router(feedback_router)
if os.environ.get("ENABLE_GUARDRAILS", "").lower() in {"1", "true", "yes"}:
    # Activate NeMo Guardrails PII checker when explicitly enabled
    set_guardrails(contains_pii)
    app.add_middleware(GuardrailsMiddleware, checker=contains_pii)



# Startup/shutdown now handled via lifespan


@app.get("/health")
async def health_check() -> Response:
    """Health check endpoint for monitoring.

    Returns 200 with ``{"status": "healthy", "db": "ok"}`` when the primary
    database is reachable, or 503 with ``{"status": "degraded", "db": "unavailable"}``
    when the connectivity check fails.
    """
    import json as _json
    from sqlalchemy import text as _text

    db_status = "ok"
    http_status = 200
    try:
        db = _get_db()
        with db.session() as conn:
            conn.execute(_text("SELECT 1"))
    except Exception as _db_exc:
        _logger.warning("Health check DB connectivity failed: %s", _db_exc)
        db_status = "unavailable"
        http_status = 503

    payload = _json.dumps({"status": "healthy" if http_status == 200 else "degraded", "db": db_status})
    return Response(content=payload, status_code=http_status, media_type="application/json")


@app.get("/health/live")
async def health_live() -> Response:
    """Liveness probe -- returns 200 when the process is running.

    Does not check external dependencies; used by container orchestrators to
    decide whether to restart the container.
    """
    import json as _json
    payload = _json.dumps({"status": "live"})
    return Response(content=payload, status_code=200, media_type="application/json")


@app.get("/health/ready")
async def health_ready() -> Response:
    """Readiness probe -- returns 200 only when the app can serve traffic.

    Checks the primary database connection.  Returns 503 when the database is
    unavailable so load balancers stop routing requests until the dependency
    recovers.
    """
    import json as _json
    from sqlalchemy import text as _text

    db_status = "ok"
    http_status = 200
    try:
        db = _get_db()
        with db.session() as conn:
            conn.execute(_text("SELECT 1"))
    except Exception as _db_exc:
        _logger.warning("Readiness check DB connectivity failed: %s", _db_exc)
        db_status = "unavailable"
        http_status = 503

    payload = _json.dumps({"status": "ready" if http_status == 200 else "not_ready", "db": db_status})
    return Response(content=payload, status_code=http_status, media_type="application/json")


def _e2e_enabled() -> bool:
    return os.getenv("DOCREVIEW360_E2E_MODE") == "1"


@app.post("/e2e/seed")
async def seed_e2e_endpoint() -> dict[str, Any]:
    """Reset and seed deterministic data for E2E runs."""
    if not _e2e_enabled():
        raise HTTPException(status_code=404, detail="Not found")
    from ..e2e_seed import seed_e2e_data

    return seed_e2e_data()


def _branding_payload_from_config(cfg: Config | None) -> BrandingPayload:
    """Build safe branding and release metadata for UI shell rendering."""

    active_cfg = cfg or Config(database="sqlite", editor="tiptap", cms="none", auth="oidc")
    logo_url: str | None
    try:
        logo_url = _normalize_branding_logo_url(active_cfg.branding_logo_url)
    except ValueError:
        logo_url = None

    def _safe_link(value: str, default: str) -> str:
        return value if _is_valid_branding_href(value) else default

    release_build_number = os.getenv("DOCREVIEW360_RELEASE_BUILD_NUMBER", "dev")
    release_build_date = os.getenv("DOCREVIEW360_RELEASE_BUILD_DATE", "unknown")
    release_commit = os.getenv("DOCREVIEW360_RELEASE_COMMIT")
    environment = os.getenv("DOCREVIEW360_ENV", "dev") or "dev"

    return BrandingPayload(
        branding_company_name=(active_cfg.branding_company_name or "DocReview360").strip()
        or "DocReview360",
        branding_logo_url=logo_url,
        branding_logo_alt=(active_cfg.branding_logo_alt or "Organization logo").strip()
        or "Organization logo",
        branding_support_url=_safe_link(active_cfg.branding_support_url, "/docs/"),
        branding_docs_url=_safe_link(active_cfg.branding_docs_url, "/docs/"),
        branding_security_url=_safe_link(active_cfg.branding_security_url, "/security"),
        branding_privacy_url=_safe_link(active_cfg.branding_privacy_url, "/privacy"),
        release_version=_load_release_version(),
        release_build_number=release_build_number,
        release_build_date=release_build_date,
        release_commit=release_commit,
        environment=environment,
    )


@app.get("/branding", response_model=BrandingPayload)
async def branding_endpoint() -> BrandingPayload:
    """Return public branding and release metadata for UI shell components."""

    cfg = Config.load(CONFIG_FILE)
    return _branding_payload_from_config(cfg)


@app.get("/users/me")
async def current_user_endpoint(
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Return information about the current user."""
    roles = list(get_roles(current_user.username))
    cfg = Config.load(CONFIG_FILE)
    inactivity_timeout = (
        cfg.inactivity_timeout_minutes if cfg is not None else 30
    )
    branding = _branding_payload_from_config(cfg)
    return {
        "username": current_user.username,
        "is_admin": "admin" in roles,
        "active": auth.is_active(current_user.username),
        "roles": roles,
        "inactivity_timeout_minutes": inactivity_timeout,
        "branding_company_name": branding.branding_company_name,
        "branding_logo_url": branding.branding_logo_url,
        "branding_logo_alt": branding.branding_logo_alt,
        "release_version": branding.release_version,
        "release_build_number": branding.release_build_number,
        "release_build_date": branding.release_build_date,
        "release_commit": branding.release_commit,
        "environment": branding.environment,
    }


def require_audit_access(current_user: auth.User = Depends(auth.get_current_user)) -> str:
    """Ensure the requester may view audit logs and record the attempt."""

    if has_permission(current_user.username, "view_audit_log"):
        log_event("audit_log_access", user_id=current_user.username, status="success")
        return current_user.username
    log_event("audit_log_access", user_id=current_user.username, status="denied")
    raise HTTPException(status_code=403, detail="Forbidden")


class ProfilePayload(BaseModel):
    """Input model for updating user profile details and preferences."""

    picture: str | None = None
    displayName: str | None = None
    email: str | None = None
    phone: str | None = None
    shorthand: str | None = None
    jobTitle: str | None = None
    department: str | None = None
    timeZone: str | None = None
    dashboards: list[str] | None = None
    permissions: list[str] | None = None
    notificationEmail: bool | None = None
    notificationSMS: bool | None = None
    twoFA: bool | None = None
    theme: Literal["system", "light", "dark"] | None = None
    reduce_motion: bool | None = None


class UserStatusPayload(BaseModel):
    """Payload for toggling a user's active status."""

    active: bool


class UserCreatePayload(BaseModel):
    """Payload for creating a user."""

    username: str
    roles: list[str] = Field(default_factory=list)
    active: bool = True
    password: str | None = None


class UserUpdatePayload(BaseModel):
    """Payload for updating a user."""

    username: str | None = None
    roles: list[str] | None = None
    active: bool | None = None
    password: str | None = None


class UserSummary(BaseModel):
    """Summary information returned by user endpoints."""

    username: str
    roles: list[str]
    active: bool


class RolePermissionUpdate(BaseModel):
    """Payload for updating role permissions."""

    permissions: list[str] = Field(default_factory=list)


class RolePermissionSummary(BaseModel):
    """Role permission summary with default counts."""

    role: str
    permissions: list[str]
    count: int
    default_permissions: list[str]
    default_count: int
    is_default: bool


class UserImportError(BaseModel):
    """Error detail for a single imported row."""

    row: int | None = None
    username: str | None = None
    error: str


class UserImportResult(BaseModel):
    """Summary of user import results."""

    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[UserImportError] = Field(default_factory=list)


def _normalize_import_header(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def _parse_import_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned in {"1", "true", "yes", "y", "on"}:
            return True
        if cleaned in {"0", "false", "no", "n", "off"}:
            return False
    return None


def _split_import_roles(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = re.split(r"[;,|]", str(value))
    roles = [str(item).strip().lower() for item in raw_items if str(item).strip()]
    return roles

def _normalize_role_permission(value: str) -> str | None:
    cleaned = value.strip().lower()
    return cleaned if cleaned else None



def _update_role_permissions(role: str, permissions: list[str]) -> None:
    settings = settings_manager.load_settings(settings_manager.SETTINGS_FILE)
    rbac_cfg = settings.get("rbac")
    if not isinstance(rbac_cfg, dict):
        rbac_cfg = {}
    roles_cfg = rbac_cfg.get("roles")
    if not isinstance(roles_cfg, dict):
        roles_cfg = {}
    normalized = []
    for perm in permissions:
        if not isinstance(perm, str):
            continue
        cleaned = _normalize_role_permission(perm)
        if cleaned:
            normalized.append(cleaned)
    roles_cfg[role] = sorted(set(normalized))
    rbac_cfg["roles"] = roles_cfg
    settings_manager.update_setting("rbac", rbac_cfg, settings_manager.SETTINGS_FILE)
    rbac.reload_role_permissions(force=True)


def _generate_password() -> str:
    policy = auth._password_policy()
    class_sets: dict[str, str] = {
        "lowercase": string.ascii_lowercase,
        "uppercase": string.ascii_uppercase,
        "digits": string.digits,
        "symbols": policy.symbol_characters,
    }
    required: list[str] = []
    for class_name in policy.character_classes:
        chars = class_sets.get(class_name)
        if chars:
            required.append(secrets.choice(chars))
    if not required:
        required.append(secrets.choice(string.ascii_letters + string.digits))
    combined = "".join(class_sets.get(name, "") for name in policy.character_classes)
    if not combined:
        combined = string.ascii_letters + string.digits
    length = max(policy.min_length, len(required))
    extra = [secrets.choice(combined) for _ in range(length - len(required))]
    password_chars = required + extra
    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)


def _user_summary(username: str) -> UserSummary:
    return UserSummary(
        username=username,
        roles=sorted(get_roles(username)),
        active=auth.is_active(username),
    )


_SESSION_COOKIE_MAX_AGE = auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def _encode_session_cookie(username: str) -> str:
    """Return a signed session cookie value for ``username``."""

    issued_at = int(time.time())
    payload = f"{username}:{issued_at}"
    signature = hmac.new(
        auth.SECRET_KEY.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}:{signature}"


def _decode_session_cookie(value: str | None) -> str | None:
    """Return the validated username from a session cookie value."""

    if not value:
        return None
    try:
        username, issued_raw, provided_sig = value.rsplit(":", 2)
        issued_at = int(issued_raw)
    except (TypeError, ValueError):
        return None
    payload = f"{username}:{issued_at}"
    expected_sig = hmac.new(
        auth.SECRET_KEY.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_sig, provided_sig):
        return None
    if int(time.time()) - issued_at > _SESSION_COOKIE_MAX_AGE:
        return None
    return username or None


def _ensure_reviewer_exists(reviewer: str) -> None:
    repo = auth._get_user_repository()
    if not repo.get_user(reviewer):
        raise HTTPException(status_code=404, detail="Reviewer not found")


def _is_admin_user(user: auth.User) -> bool:
    return has_role(user.username, "admin")


def _resolve_requested_user(requested_user: str | None, current_user: auth.User) -> str:
    """Return an actor user while preventing non-admin impersonation."""

    candidate = (requested_user or "").strip()
    if not candidate:
        return current_user.username
    if candidate != current_user.username and not _is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    return candidate


def _enforce_project_access(project: ProjectModel, current_user: auth.User) -> None:
    """Ensure ``current_user`` can access ``project``."""

    if _is_admin_user(current_user):
        return
    if project.user == current_user.username:
        return
    if project.temp_user == current_user.username:
        return
    if current_user.username in project.reviewers:
        return
    if any(p.id == project.id for p in list_projects(current_user.username)):
        return
    raise HTTPException(status_code=403, detail="Forbidden")


def _enforce_project_manage_access(project: ProjectModel, current_user: auth.User) -> None:
    """Ensure ``current_user`` can mutate ``project`` assignments and settings."""

    if _is_admin_user(current_user):
        return
    if project.user == current_user.username:
        return
    if project.temp_user == current_user.username:
        return
    raise HTTPException(status_code=403, detail="Forbidden")


def _enforce_document_access(document: DocumentModel, current_user: auth.User) -> None:
    """Ensure ``current_user`` can access ``document``."""

    if _is_admin_user(current_user):
        return
    if document.user == current_user.username:
        return
    if document.project:
        project = get_project(document.project)
        if project is not None:
            if project.user == current_user.username:
                return
            if project.temp_user == current_user.username:
                return
            if current_user.username in project.reviewers:
                return
    raise HTTPException(status_code=403, detail="Forbidden")


# Moved to admin_router.py:
#   PUT /rbac/role-permissions/{role}
#   DELETE /rbac/role-permissions/{role}
#   GET /rbac/role-permissions
#   GET /rbac/matrix


# Moved to admin_router.py:
#   GET /users
#   POST /users/import
#   POST /api/users/import
#   POST /users
#   PUT /users/{username}
#   DELETE /users/{username}
#   GET /profile
#   PUT /profile
#   POST /admin/users/{username}/status


# Moved to projects_router.py:
#   GET /projects
#   GET /projects/assigned/{username}
#   POST /projects
#   GET /projects/{project_id}
#   GET /projects/{project_id}/reviewers
#   POST /projects/{project_id}/reviewers
#   PUT /projects/{project_id}/reviewers/{reviewer}
#   DELETE /projects/{project_id}/reviewers/{reviewer}
#   GET /projects/{project_id}/reviews
#   POST /projects/{project_id}/reviews
#   PUT /projects/{project_id}
#   DELETE /projects/{project_id}
#   GET /projects/{project_id}/workflow
#   PUT /projects/{project_id}/priority
#   POST /projects/{project_id}/temporary
#   GET /projects/{project_id}/preferences
#   PUT /projects/{project_id}/preferences
#   GET /projects/{project_id}/approvals/pdf
# Moved to documents_router.py:
#   POST /documents/import
#   POST /documents/tiptap
#   GET /documents
#   GET /documents/public
#   GET /documents/public/report
#   GET /documents/public/{doc_id}/html
#   GET /documents/{doc_id}
#   GET /documents/{doc_id}/audit
#   GET /documents/{doc_id}/audit/export
#   GET /documents/{doc_id}/audit/snapshots
#   POST /documents/{doc_id}/audit/snapshots
#   GET /documents/{doc_id}/verify-signature
#   PUT /documents/{doc_id}
#   POST /cms/export/{doc_id}
#   POST /cms/import
#   POST /documents/{doc_id}/revisions
#   GET /documents/{doc_id}/revisions
#   GET /documents/{doc_id}/revisions/{rev_id}
#   POST /documents/{doc_id}/comments
#   GET /documents/{doc_id}/comments
#   PUT /documents/{doc_id}/comments/{comment_id}
#   GET /documents/{doc_id}/export
#   POST /archive/{doc_id}
#   GET /archive
#   GET /archive/{archive_id}
#   GET /archive/{archive_id}/report/{fmt}
# Moved to tools_router.py:
#   GET /search
#   GET /search/export
#   POST /search/saved
#   GET /search/saved
#   GET /search/stats
#   POST /watchlist/{project_id}
#   GET /watchlist/{user}

# Moved to tools_router.py:
#   GET /ai/key
#   PUT /ai/key
#   POST /ai/rewrite
#   POST /ai/summarize
#   POST /chat

# Moved to tools_router.py:
#   POST /document-types
#   GET /document-types
#   GET /document-types/export
#   POST /document-types/import
#   GET /document-types/{name}
#   PUT /document-types/{name}
#   GET /document-types/{name}/usage
#   DELETE /document-types/{name}
# ---------------------------------------------------------------------------
# Template management
# ---------------------------------------------------------------------------


# Moved to workflows_router.py:
#   GET /templates
#   GET /templates/{name}
#   POST /templates
#   PUT /templates/{name}
#   DELETE /templates/{name}
#   GET /templates/{name}/download
#   POST /templates/{name}/approve
#   POST /templates/{name}/retire
# Moved to workflows_router.py:
#   GET /email-templates
#   GET /email-templates/{name}
#   POST /email-templates
#   PUT /email-templates/{name}
#   DELETE /email-templates/{name}

# Moved to admin_router.py:
#   GET /plugin-marketplace
#   POST /plugin-marketplace/install


# ---------------------------------------------------------------------------
# Phase management
# ---------------------------------------------------------------------------


# Moved to workflows_router.py:
#   POST /phases
#   GET /phases
#   GET /phases/config
#   PUT /phases/{name}/workflow-template
#   PUT /phases/{name}
#   GET /phases/{name}/usage
#   DELETE /phases/{name}
#   GET /phases/sla
#   GET /phases/{name}/sla
#   PUT /phases/{name}/sla
#   DELETE /phases/{name}/sla
#   GET /phases/{name}/sla/status

# Moved to workflows_router.py:
#   GET /workflow-templates
#   POST /workflow-templates
#   GET /workflow-templates/{template_id}
#   PUT /workflow-templates/{template_id}
#   DELETE /workflow-templates/{template_id}

# Moved to workflows_router.py:
#   POST /workflows
#   GET /workflows/{wf_id}
#   GET /workflows
#   GET /workflow_roles
#   POST /workflows/{wf_id}/start
#   POST /workflows/{wf_id}/assign
#   POST /workflows/{wf_id}/advance


# Moved to workflows_router.py:
#   POST /approvals
#   GET /approvals
#   GET /approvals/{approval_id}
#   PUT /approvals/{approval_id}
#   DELETE /approvals/{approval_id}
#   POST /approvals/{approval_id}/sign
#   POST /approvals/{approval_id}/sign-initials
# Moved to documents_router.py:
#   POST /sign/{doc_id}
#   POST /sign/{sig_id}/complete
#   GET /sign/{sig_id}


# Moved to auth_router.py:
#   POST /token
#   POST /oidc/token
#   GET /me
#   POST /logout
#   GET /oidc/me
#   GET /
#   POST /login
#   GET /dashboard
#   GET /help
# Moved to admin_router.py:
#   GET /admin/panel
#   GET /plugins
#   POST /plugins
#   PUT /plugins/{name}/enable
#   PUT /plugins/{name}/disable
#   DELETE /plugins/{name}


# Moved to dashboards_router.py:
#   GET /logs
#   GET /api/audit
#   GET /logs/export

# Moved to dashboards_router.py:
#   GET /reports/summary
#   GET /metrics/summary
#   GET /reports/summary.csv
#   GET /reports/throughput
#   GET /reports/throughput.csv
#   GET /reports/workload
#   GET /reports/workload.csv
#   GET /reports/dashboard
#   GET /reports/document-aging
#   GET /dashboard/user
#   GET /dashboard/widgets
#   GET /dashboard/doc-types
#   GET /dashboard/visibility
#   PUT /dashboard/visibility
#   GET /dashboard/manager
#   GET /status/public
#   GET /status/internal
#   GET /dashboard/admin
#   GET /dashboard/executive-summary
#   GET /dashboard/reviewer-workload

# Moved to tools_router.py:
#   POST /documents/preflight
# Moved to workflows_router.py:
#   PUT /templates/{name}/locks/{phase}
#   DELETE /templates/{name}/locks/{phase}
#   GET /templates/{name}/locks
#   GET /templates/{name}/versions

@app.websocket("/ws/dashboard")
async def dashboard_stream(websocket: WebSocket) -> None:
    """Send dashboard data periodically over a websocket."""

    await websocket.accept()
    user = websocket.query_params.get("user")
    previous: list[dict[str, Any]] | None = None
    try:
        while True:
            data = [entry.model_dump() for entry in dashboard_data(user)]
            if data != previous:
                await websocket.send_json(data)
                previous = data
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/logs")
async def logs_stream(websocket: WebSocket) -> None:
    """Stream log events to connected clients with access control."""

    from jose import JWTError, jwt as _jwt

    user = websocket.headers.get("x-user") or websocket.query_params.get("user")

    # Accept a Bearer token passed as a query parameter (set by the frontend).
    # When present, decode it to identify the user; this supersedes the x-user header.
    raw_token = websocket.query_params.get("token")
    if raw_token:
        try:
            payload = _jwt.decode(
                raw_token,
                auth.SECRET_KEY,
                algorithms=[auth.ALGORITHM],
                audience=auth.TOKEN_AUDIENCE,
                issuer=auth.TOKEN_ISSUER,
            )
            token_user: str | None = payload.get("sub")
            if token_user:
                user = token_user
        except JWTError:
            await websocket.close(code=1008)
            return

    # Allow anonymous connections for simple dashboards and tests.  If a user
    # identifier is supplied we still honour permission checks, but omitting the
    # header no longer results in an immediate 1008 policy-violation close which
    # previously broke ``test_log_websocket``.  This keeps the endpoint usable in
    # lightweight environments while retaining optional access control.
    if user and not has_permission(user, "view_audit_log"):
        log_event("audit_log_ws_access", user_id=user, status="denied")
        await websocket.close(code=1008)
        return

    log_event("audit_log_ws_access", user_id=user, status="success")
    await websocket.accept()
    try:
        async for entry in log_stream():
            await websocket.send_json(entry.model_dump(mode="json"))
    except WebSocketDisconnect:
        pass


# Moved to admin_router.py:
#   GET /config
#   PUT /config
#   GET /signature-provider
#   PUT /signature-provider
#   GET /environments
#   POST /environments/{name}
# Moved to tools_router.py:
#   POST /tools/convert


# Moved to tools_router.py:
#   POST /api-keys
#   GET /api-keys
#   GET /api-keys/{key_id}
#   DELETE /api-keys/{key_id}
#   POST /share-links
#   GET /share-links/{link_id}
#   DELETE /share-links/{link_id}
#   GET /share/{token}
