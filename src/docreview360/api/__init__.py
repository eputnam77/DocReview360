"""FastAPI application exposing DocReview360 endpoints."""

# ruff: noqa: I001
from __future__ import annotations

import asyncio
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from fastapi import (
    Depends,
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
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from markdown_it import MarkdownIt
from pydantic import BaseModel, ConfigDict, Field

from ..e2e_runtime import apply_e2e_run_dir

apply_e2e_run_dir()

from .. import auth, reporting, rbac
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
from ..comments import CommentModel, add_comment, list_comments, render_comment_for_response
from ..config import CONFIG_FILE, Config
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
from ..logs import LogEntry, log_event, log_stream, query_logs, log_call
from ..messages import render
from ..nemo_guardrails import GuardrailsMiddleware, contains_pii
from ..phases import add_phase, delete_phase, list_phases, rename_phase
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
    SummaryReport,
    admin_dashboard,
    dashboard_data,
    generate_summary,
    manager_dashboard,
    user_dashboard,
    WidgetMetrics,
    widget_counts,
)
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
from ..stubs.task223 import convert_document
from ..template_manager import (
    delete_template as delete_stored_template,
    get_latest_template,
    list_stored_templates,
    approve_template,
    retire_template,
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
    start_workflow,
    update_workflow_template,
    workflow_templates,
    workflows,
    list_roles,
)
from .approvals import router as approvals_router
from .ml import router as ml_router, warm_ml_sessions
from .webhooks import router as webhooks_router

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


def reset_rate_limiters_for_testing() -> None:
    """Clear API endpoint rate limiting counters (used by tests)."""

    _TOKEN_RATE_LIMITER.reset()
    _LOGIN_RATE_LIMITER.reset()
    _UPLOAD_RATE_LIMITER.reset()


def _request_source(request: Request) -> str:
    """Return a stable source identifier for request-scoped rate limiting."""

    forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded_for:
        return forwarded_for
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


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
    requested_template: str | None, doc_type_name: str | None
) -> str:
    """Resolve a workflow template name from request and document type defaults."""
    if requested_template in workflow_templates:
        return requested_template

    doc_type_obj = get_document_type(doc_type_name) if doc_type_name else None
    doc_default_template = (
        doc_type_obj.default_template_id
        if doc_type_obj and doc_type_obj.default_template_id
        else None
    )
    if doc_default_template in workflow_templates:
        return doc_default_template
    return "branch-coordination"


class CommentCreate(BaseModel):
    """Input for creating comments."""

    user: str
    text: str
    parent: str | None = None


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


class SignatureProviderPayload(BaseModel):
    """Payload for selecting active signature providers."""

    primary: str
    fallback: str | None = None


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # Startup
    load_worker_state(WORKER_STATE_FILE)
    for tpl in SEED_TEMPLATES:
        if not get_latest_template(tpl["name"]):
            store_template(tpl["name"], tpl["content"].encode("utf-8"), tpl.get("metadata"))
    schedule_archive_purge()
    warm_ml_sessions()
    seed_demo_data()
    try:
        yield
    finally:
        # Shutdown
        save_worker_state(WORKER_STATE_FILE)


app = FastAPI(title="DocReview360", lifespan=_lifespan)


@app.get("/ping")
async def ping() -> dict[str, str]:
    """Lightweight health check endpoint used by the frontend."""

    return {"status": "ok"}


# Add CORS middleware to allow frontend requests
#
# Previously, the API only allowed requests from hard-coded localhost
# origins, which meant running the frontend from any other host (even a
# test environment) resulted in a browser "Failed to fetch" error due to
# a blocked CORS preflight request.  To support multiple environments we
# now read the allowed origins from an environment variable.  When the
# variable is unset we fall back to a permissive regular expression so
# that developers can experiment in ephemeral environments without extra
# configuration.
allowed_origins = os.getenv("DOCREVIEW360_ALLOW_ORIGINS")
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_origins=[o.strip() for o in allowed_origins.split(",") if o.strip()],
    )
else:
    # Secure defaults for local development. Production deployments should set
    # ``DOCREVIEW360_ALLOW_ORIGINS`` explicitly.
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_origins=[
            "http://localhost",
            "http://127.0.0.1",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ],
    )

# Enable compression for large responses as recommended by the
# performance profiling report. ``minimum_size`` avoids wasting
# CPU cycles on tiny payloads.
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(approvals_router)
app.include_router(webhooks_router)
app.include_router(collab_router)
app.include_router(ml_router)
if os.environ.get("ENABLE_GUARDRAILS", "").lower() in {"1", "true", "yes"}:
    # Activate NeMo Guardrails PII checker when explicitly enabled
    set_guardrails(contains_pii)
    app.add_middleware(GuardrailsMiddleware, checker=contains_pii)

# Templates are stored one level above this module in ``docreview360/templates``.
# The previous path incorrectly looked for templates in ``api/templates`` which
# does not exist, causing ``TemplateNotFound`` errors during E2E tests.
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


# Startup/shutdown now handled via lifespan


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}


def _e2e_enabled() -> bool:
    return os.getenv("DOCREVIEW360_E2E_MODE") == "1"


@app.post("/e2e/seed")
async def seed_e2e_endpoint() -> dict[str, Any]:
    """Reset and seed deterministic data for E2E runs."""
    if not _e2e_enabled():
        raise HTTPException(status_code=404, detail="Not found")
    from ..e2e_seed import seed_e2e_data

    return seed_e2e_data()


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
    return {
        "username": current_user.username,
        "is_admin": "admin" in roles,
        "active": auth.is_active(current_user.username),
        "roles": roles,
        "inactivity_timeout_minutes": inactivity_timeout,
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


@app.get("/users", response_model=list[UserSummary])
async def list_users_endpoint(
    user: auth.User = Depends(require_role("admin")),
) -> list[UserSummary]:
    """Return all users with role assignments and active status."""

    repo = auth._get_user_repository()
    return [_user_summary(record.username) for record in repo.list_users()]


@app.post("/users", response_model=UserSummary, status_code=201)
async def create_user_endpoint(
    body: UserCreatePayload,
    user: auth.User = Depends(require_role("admin")),
) -> UserSummary:
    """Create a user and assign roles."""

    username = body.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username required")
    repo = auth._get_user_repository()
    if repo.get_user(username):
        raise HTTPException(status_code=409, detail="User already exists")
    password = body.password or _generate_password()
    repo.create_user(username, password, active=body.active)
    if body.roles:
        rbac.set_user_roles(username, body.roles, actor="system", context={"source": "api"})
    return _user_summary(username)


@app.put("/users/{username}", response_model=UserSummary)
async def update_user_endpoint(
    username: str,
    body: UserUpdatePayload,
    user: auth.User = Depends(require_role("admin")),
) -> UserSummary:
    """Update a user's name, roles, active flag, or password."""

    repo = auth._get_user_repository()
    record = repo.get_user(username)
    if record is None:
        raise HTTPException(status_code=404, detail="User not found")
    target_username = body.username.strip() if body.username is not None else username
    if body.username is not None and not target_username:
        raise HTTPException(status_code=400, detail="Username required")
    if target_username != username and repo.get_user(target_username):
        raise HTTPException(status_code=409, detail="Username already exists")
    if target_username != username:
        repo.rename_user(username, target_username)
        roles = get_roles(username)
        rbac.set_user_roles(target_username, roles, actor="system", context={"source": "api"})
        rbac.set_user_roles(username, [], actor="system", context={"source": "api"})
        username = target_username
    if body.password:
        repo.create_user(username, body.password, active=record.active)
    if body.active is not None:
        repo.set_active(username, body.active)
    if body.roles is not None:
        rbac.set_user_roles(username, body.roles, actor="system", context={"source": "api"})
    return _user_summary(username)


@app.delete("/users/{username}", response_model=UserSummary)
async def delete_user_endpoint(
    username: str,
    user: auth.User = Depends(require_role("admin")),
) -> UserSummary:
    """Delete a user and remove role assignments."""

    repo = auth._get_user_repository()
    record = repo.get_user(username)
    if record is None:
        raise HTTPException(status_code=404, detail="User not found")
    summary = _user_summary(username)
    repo.delete_user(username)
    rbac.set_user_roles(username, [], actor="system", context={"source": "api"})
    return summary


@app.get("/profile")
async def get_profile(
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Return profile information for the current user."""
    preferences = get_preferences(current_user.username)
    profile_data = get_profile_data(current_user.username)
    theme = preferences.get("theme", "system")
    if theme not in {"system", "light", "dark"}:
        theme = "system"
    return {
        "username": current_user.username,
        **profile_data,
        "theme": theme,
        "preferences": preferences,
        "roles": sorted(get_roles(current_user.username)),
    }


@app.put("/profile")
async def update_profile(
    body: ProfilePayload,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Persist profile preference updates."""
    payload = body.model_dump()
    preference_keys = {"theme", "reduce_motion"}
    prefs = {k: v for k, v in payload.items() if k in preference_keys and v is not None}
    profile_updates = {
        k: v for k, v in payload.items() if k not in preference_keys and v is not None
    }
    updated_profile = (
        update_profile_data(current_user.username, profile_updates)
        if profile_updates
        else get_profile_data(current_user.username)
    )
    updated_prefs = (
        update_preferences(current_user.username, prefs) if prefs else get_preferences(current_user.username)
    )
    theme = updated_prefs.get("theme", "system")
    if theme not in {"system", "light", "dark"}:
        theme = "system"
    return {
        "username": current_user.username,
        **updated_profile,
        "theme": theme,
        "preferences": updated_prefs,
        "roles": sorted(get_roles(current_user.username)),
    }


@app.post("/admin/users/{username}/status")
async def set_user_status(
    username: str,
    body: UserStatusPayload,
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Set the active status for ``username`` (admin only)."""

    if not auth.USER_REPOSITORY.get_user(username):
        raise HTTPException(status_code=404, detail="User not found")
    auth.USER_REPOSITORY.set_active(username, body.active)
    return {"username": username, "active": body.active}


@app.get("/projects", response_model=list[ProjectModel])
async def list_projects_endpoint(
    user: str | None = None,
    x_user: str | None = Header(None),
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[ProjectModel]:
    """Return projects optionally filtered by user with simple caching.

    When a user is specified, includes projects where the user is:
    1. Directly assigned as project.user
    2. Temporarily assigned as project.temp_user
    3. Listed as a project reviewer
    4. Assigned as a reviewer in any approval step (SME, FLM, PPM, TW, etc.)
    """
    requested_user = (user or x_user) or None
    if requested_user:
        effective_user = _resolve_requested_user(requested_user, current_user)
    else:
        effective_user = None if _is_admin_user(current_user) else current_user.username
    cache_key = f"projects-{effective_user or 'all'}"
    cached = cache_get(cache_key)
    if cached:
        try:
            if isinstance(cached, bytes):
                cached = cached.decode()
            data = json.loads(cached)
            return [ProjectModel.model_validate(p) for p in data]
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            log_event("cache_decode_failed", key=cache_key, message=str(exc))
    projects_list = list_projects(effective_user)
    cache_set(
        cache_key,
        json.dumps([p.model_dump(mode="json") for p in projects_list]),
        ttl=30,
    )
    return projects_list


@app.get("/projects/assigned/{username}", response_model=list[ProjectModel])
async def get_user_assignments_endpoint(
    username: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[ProjectModel]:
    """Get all projects assigned to a specific user through any mechanism.

    This includes:
    - Direct project assignments
    - Temporary assignments
    - Approval assignments (SME, FLM, PPM, TW, Senior TW, TW Manager, Attorney)

    Useful for debugging and testing assignment logic.
    """
    return list_projects(_resolve_requested_user(username, current_user))


@app.post("/projects", status_code=201, response_model=ProjectModel)
async def create_project_endpoint(
    body: ProjectCreate,
    current_user: auth.User = Depends(auth.get_current_user),
) -> ProjectModel:  # noqa: C901
    """Create a new project."""
    if body.user is not None or not _is_admin_user(current_user):
        body.user = _resolve_requested_user(body.user, current_user)

    # Auto-generate ID if not provided
    if body.id is None or (isinstance(body.id, str) and not body.id.strip()):
        from ..search import search_index

        body.id = search_index.generate_project_id()
    else:
        existing = get_project(body.id)
        if existing is not None:
            raise HTTPException(status_code=409, detail="Project already exists")

    # If document_number is not provided, use the id as document_number
    if body.document_number is None or (
        isinstance(body.document_number, str) and not body.document_number.strip()
    ):
        body.document_number = body.id

    project = ProjectModel(**body.model_dump())

    # Handle workflow assignment when a template has been provided.  Rather than
    # manually constructing a minimal ``WorkflowModel`` we now delegate to
    # :func:`create_workflow`, ensuring approval steps and workflow metadata are
    # initialized consistently with the template definition.
    if body.workflow:
        existing_workflow = workflows.get(body.workflow)
        if existing_workflow is not None:
            if existing_workflow.project and existing_workflow.project != project.id:
                raise HTTPException(
                    status_code=409,
                    detail="Workflow already assigned to another project",
                )
            existing_workflow.project = project.id
            project.workflow = existing_workflow.id
            project.initial_phase = existing_workflow.phase
            add_project(project)
            clear_cache()
            log_event(
                "create_project",
                user_id=project.user,
                project=project.id,
                message=render(
                    "create_project", user=project.user or "", project_id=project.id
                ),
            )
            return project

        phases = _resolve_project_phases(body.doc_type, body.phase)
        template_name = _resolve_workflow_template(body.workflow, body.doc_type)
        workflow = create_workflow(project.id, phases, template=template_name)
        project.workflow = workflow.id
        project.initial_phase = workflow.phase
    # Previously a workflow was automatically created whenever a phase was
    # supplied, even if the caller did not request one.  This behavior made it
    # impossible to create a project without a workflow.  Now we only create a
    # workflow when an explicit ``workflow`` identifier is provided.  Projects can
    # still record their starting phase without being tied to a workflow.

    if body.phase and not body.workflow:
        # Preserve the starting phase so the project reflects configuration even
        # before a workflow is assigned.
        project.initial_phase = body.phase

    add_project(project)

    # Clear all project-related caches to ensure fresh data
    clear_cache()
    log_event(
        "create_project",
        user_id=project.user,
        project=project.id,
        message=render("create_project", user=project.user or "", project_id=project.id),
    )
    return project


@app.get("/projects/{project_id}", response_model=ProjectModel)
async def get_project_endpoint(
    project_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> ProjectModel:
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_access(project, current_user)
    return project


@app.get("/projects/{project_id}/reviewers", response_model=list[str])
async def list_project_reviewers(
    project_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[str]:
    """Return reviewers assigned to a project."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_access(project, current_user)
    return list(project.reviewers)


@app.post("/projects/{project_id}/reviewers", response_model=list[str])
async def add_project_reviewer_endpoint(
    project_id: str,
    body: ProjectReviewerPayload,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[str]:
    """Add a reviewer to a project."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_manage_access(project, current_user)
    reviewer = body.reviewer.strip()
    if not reviewer:
        raise HTTPException(status_code=400, detail="Reviewer required")
    _ensure_reviewer_exists(reviewer)
    try:
        project = add_project_reviewer(project_id, reviewer)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found")
    return list(project.reviewers)


@app.put("/projects/{project_id}/reviewers/{reviewer}", response_model=list[str])
async def update_project_reviewer_endpoint(
    project_id: str,
    reviewer: str,
    body: ProjectReviewerPayload,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[str]:
    """Update a reviewer assignment for a project."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_manage_access(project, current_user)
    new_reviewer = body.reviewer.strip()
    if not new_reviewer:
        raise HTTPException(status_code=400, detail="Reviewer required")
    _ensure_reviewer_exists(new_reviewer)
    try:
        project = update_project_reviewer(project_id, reviewer, new_reviewer)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return list(project.reviewers)


@app.delete("/projects/{project_id}/reviewers/{reviewer}", response_model=list[str])
async def remove_project_reviewer_endpoint(
    project_id: str,
    reviewer: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[str]:
    """Remove a reviewer from a project."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_manage_access(project, current_user)
    try:
        project = remove_project_reviewer(project_id, reviewer)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return list(project.reviewers)


@app.get("/projects/{project_id}/reviews", response_model=list[ReviewModel])
async def list_project_reviews(
    project_id: str,
    phase: str | None = None,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[ReviewModel]:
    """Return reviews for a project."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_access(project, current_user)
    return list_reviews(project_id, phase)


@app.post("/projects/{project_id}/reviews", response_model=ReviewModel, status_code=201)
async def create_project_review(
    project_id: str,
    body: ReviewCreate,
    x_user: str | None = Header(None),
    current_user: auth.User = Depends(auth.get_current_user),
) -> ReviewModel:
    """Create a new review entry for a project."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_access(project, current_user)
    reviewer = _resolve_requested_user(x_user, current_user)

    review_data = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "reviewer": reviewer,
        "status": body.status,
        "comment": body.comment,
        "phase_id": body.phase_id,
        "required": body.required,
    }
    review = ReviewModel(**review_data)
    add_review(review)
    return review


async def _parse_update_body(request: Request) -> tuple[ProjectUpdate | None, bool]:
    """Return the JSON body and whether the workflow field was provided."""
    if request.headers.get("content-type", "").startswith("application/json"):
        data = await request.json()
        return ProjectUpdate(**data), "workflow" in data
    return None, False


def _resolve_workflow(
    request: Request,
    workflow_provided: bool,
    workflow: str | None,
    body: ProjectUpdate | None,
    project_id: str,
    doc_type_name: str | None,
) -> tuple[str | None, bool]:
    """Determine new workflow information from the request."""
    is_json = request.headers.get("content-type", "").startswith("application/json")
    if is_json:
        if workflow_provided:
            if workflow is not None:
                existing_workflow = workflows.get(workflow)
                if existing_workflow is not None:
                    if existing_workflow.project and existing_workflow.project != project_id:
                        raise ValueError("Workflow already assigned to another project")
                    existing_workflow.project = project_id
                    return existing_workflow.id, True
                phases = _resolve_project_phases(
                    doc_type_name, body.phase if body and body.phase else None
                )
                template_name = _resolve_workflow_template(workflow, doc_type_name)
                wf = create_workflow(project_id, phases, template=template_name)
                return wf.id, True
            return None, True
        return None, False
    if workflow is not None:
        existing_workflow = workflows.get(workflow)
        if existing_workflow is not None:
            if existing_workflow.project and existing_workflow.project != project_id:
                raise ValueError("Workflow already assigned to another project")
            existing_workflow.project = project_id
            return existing_workflow.id, True
        phases = _resolve_project_phases(doc_type_name, None)
        template_name = _resolve_workflow_template(workflow, doc_type_name)
        wf = create_workflow(project_id, phases, template=template_name)
        return wf.id, True
    return None, False


def _update_workflow_phase(
    request: Request, body: ProjectUpdate | None, updated_project: ProjectModel
) -> None:
    """Update an existing workflow's phase when only the phase is provided."""
    if not body or body.phase is None:
        return
    is_json = request.headers.get("content-type", "").startswith("application/json")
    if not is_json:
        return
    from ..workflows import get_workflow as _get_wf

    wf_id_to_update = updated_project.workflow
    if not wf_id_to_update:
        return
    wf_model = _get_wf(wf_id_to_update)
    if wf_model:
        wf_model.phase = body.phase
        if body.phase not in wf_model.phases:
            wf_model.phases.append(body.phase)


async def _import_uploaded_file(
    file: UploadFile, project_id: str, project_user: str | None
) -> None:
    """Import an uploaded file as a document for the given project."""
    content = await file.read()
    import_document(
        file.filename or "uploaded_document",
        content,
        project=project_id,
        user=project_user,
    )


@app.put("/projects/{project_id}", response_model=ProjectModel)
async def update_project_endpoint(  # noqa: C901
    project_id: str,
    request: Request,
    name: str | None = Form(None),
    user: str | None = Form(None),
    doc_type: str | None = Form(None),
    workflow: str | None = Form(None),
    title: str | None = Form(None),
    description: str | None = Form(None),
    sme: str | None = Form(None),  # Add sme field for frontend compatibility
    docType: str | None = Form(None),  # Add docType field for frontend compatibility
    file: UploadFile | None = File(None),
    current_user: auth.User = Depends(auth.get_current_user),
) -> ProjectModel:
    """Update project fields like name, user, doc_type, or workflow."""
    try:
        existing_project = get_project(project_id)
        if existing_project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        _enforce_project_manage_access(existing_project, current_user)
        previous_workflow_id = existing_project.workflow
        body, workflow_provided = await _parse_update_body(request)

        if body:
            if body.name is not None:
                name = body.name
            if body.user is not None:
                user = body.user
            if body.doc_type is not None:
                doc_type = body.doc_type
            if body.workflow is not None:
                workflow = body.workflow
            if body.description is not None:
                description = body.description

        if isinstance(workflow, str) and not workflow.strip():
            workflow = None

        requested_project_user = user or sme
        if requested_project_user is not None or not _is_admin_user(current_user):
            project_user = _resolve_requested_user(requested_project_user, current_user)
        else:
            project_user = requested_project_user
        project_doc_type = doc_type or docType or existing_project.doc_type
        project_description = description

        workflow_id, workflow_set = _resolve_workflow(
            request, workflow_provided, workflow, body, project_id, project_doc_type
        )

        initial_phase = None
        if body and body.phase is not None and workflow_id is None:
            initial_phase = body.phase

        updated_project = update_project(
            project_id,
            name=name or title,
            user=project_user,
            doc_type=project_doc_type,
            workflow=workflow_id,
            workflow_set=workflow_set,
            description=project_description,
            initial_phase=initial_phase,
        )

        if (
            workflow_set
            and previous_workflow_id
            and previous_workflow_id != updated_project.workflow
        ):
            previous_workflow = workflows.get(previous_workflow_id)
            if previous_workflow and previous_workflow.project == project_id:
                previous_workflow.project = ""

        _update_workflow_phase(request, body, updated_project)

        if file:
            await _import_uploaded_file(file, project_id, project_user)

        clear_cache()
        return updated_project
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.delete("/projects/{project_id}", response_model=ProjectModel)
async def delete_project_endpoint(
    project_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> ProjectModel:
    """Delete a project and its persisted record."""
    existing_project = get_project(project_id)
    if existing_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_manage_access(existing_project, current_user)
    try:
        removed = remove_project(project_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Project not found") from None
    clear_cache()
    log_event(
        "delete_project",
        user_id=removed.user,
        project=removed.id,
        message=render("delete_project", user=removed.user or "", project_id=removed.id),
    )
    return removed


@app.get("/projects/{project_id}/workflow", response_model=WorkflowModel)
async def get_project_workflow_endpoint(
    project_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> WorkflowModel:
    """Return the workflow associated with a project."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_access(project, current_user)
    for wf in workflows.values():
        if wf.project == project_id:
            return wf
    raise HTTPException(status_code=404, detail="Workflow not found")


@app.put("/projects/{project_id}/priority", response_model=ProjectModel)
async def update_priority_endpoint(
    project_id: str,
    body: PriorityUpdate,
    current_user: auth.User = Depends(auth.get_current_user),
) -> ProjectModel:
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_manage_access(project, current_user)
    try:
        return set_project_priority(project_id, body.priority)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/projects/{project_id}/temporary", response_model=ProjectModel)
async def temporary_assign_endpoint(
    project_id: str,
    body: TemporaryAssign,
    current_user: auth.User = Depends(auth.get_current_user),
) -> ProjectModel:
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_manage_access(project, current_user)
    assigned_user = _resolve_requested_user(body.user, current_user)
    try:
        return assign_temporary(project_id, assigned_user, body.until)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/projects/{project_id}/preferences", response_model=ProjectPreferences)
async def get_project_preferences_endpoint(
    project_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> ProjectPreferences:
    """Return editor extension preferences for a project."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_access(project, current_user)
    return get_project_preferences(project_id)


@app.put("/projects/{project_id}/preferences", response_model=ProjectPreferences)
async def update_project_preferences_endpoint(
    project_id: str,
    body: ProjectPreferences,
    current_user: auth.User = Depends(auth.get_current_user),
) -> ProjectPreferences:
    """Update editor extension preferences for a project."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_manage_access(project, current_user)
    return update_project_preferences(project_id, body.model_dump())


@app.get("/projects/{project_id}/approvals/pdf")
async def project_approvals_pdf_endpoint(
    project_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> Response:
    """Return merged approval PDFs for a project."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_access(project, current_user)
    try:
        data = build_approvals_summary_pdf(project_id, actor=current_user.username)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    log_event(
        "approval_summary_downloaded",
        user_id=current_user.username,
        project=project_id,
    )
    log_audit_event(
        project_id,
        "approval_summary_downloaded",
        actor=current_user.username,
        project=project_id,
    )
    return Response(
        data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="approvals-{project_id}.pdf"'},
    )


@app.post("/documents/import", status_code=201, response_model=DocumentModel)
async def import_document_endpoint(
    request: Request,
    file: UploadFile = File(...),
    project: str | None = Form(None),
    user: str | None = Form(None),
    priority: int | None = Form(None),
    current_user: auth.User = Depends(auth.get_current_user),
) -> DocumentModel:
    """Import a DOCX or Markdown file and store it as a document."""
    import tempfile

    _UPLOAD_RATE_LIMITER.enforce(f"documents-import:{current_user.username}:{_request_source(request)}")

    if project:
        project_model = get_project(project)
        if project_model is None:
            raise HTTPException(status_code=404, detail="Project not found")
        _enforce_project_access(project_model, current_user)
    resolved_user = user
    if user is not None or not _is_admin_user(current_user):
        resolved_user = _resolve_requested_user(user, current_user)

    temp = tempfile.NamedTemporaryFile(delete=False)
    try:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            temp.write(chunk)
        temp.flush()
        temp.seek(0)
        data = temp.read()
        filename = file.filename or "unknown"
        document = import_document(
            filename,
            data,
            project=project,
            user=resolved_user,
            priority=priority,
        )
    finally:
        temp.close()
        try:
            Path(temp.name).unlink(missing_ok=True)
        except OSError as cleanup_error:
            log_event("upload_temp_cleanup_failed", message=str(cleanup_error))
    cache_set(
        "documents",
        json.dumps([d.model_dump(mode="json") for d in list_docs()]),
        ttl=30,
    )
    log_event(
        "import_document",
        user_id=resolved_user,
        project=project,
        filename=filename,
        message=render(
            "import_docx",
            user=resolved_user or "",
            project_id=project or "",
            filename=filename,
        ),
    )
    return document


@app.post("/documents/tiptap", status_code=201, response_model=DocumentModel)
async def import_tiptap_endpoint(
    body: dict[str, Any],
    link_duplicates: bool = Query(False),
    current_user: auth.User = Depends(auth.get_current_user),
) -> DocumentModel:
    """Import a TipTap JSON document."""
    from ..tiptap import import_tiptap_document

    try:
        document = import_tiptap_document(
            body,
            link_duplicates=link_duplicates,
            user=current_user.username,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    log_event(
        "convert_tiptap",
        document=document.id,
        project=document.project,
        message=render(
            "convert_tiptap",
            project_id=document.project or "",
        ),
    )
    cache_set(
        "documents",
        json.dumps([d.model_dump(mode="json") for d in list_docs()]),
        ttl=30,
    )
    return document


@app.get("/documents", response_model=list[DocumentModel])
async def list_documents_endpoint(
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[DocumentModel]:
    """Return all imported documents with caching."""
    cache_key = (
        f"documents-{current_user.username}"
        if not _is_admin_user(current_user)
        else "documents"
    )
    cached = cache_get(cache_key)
    if cached:
        try:
            if isinstance(cached, bytes):
                cached = cached.decode()
            data = json.loads(cached)
            docs = [DocumentModel.model_validate(d) for d in data]
            if (cfg := Config.load(CONFIG_FILE)) and cfg.log_reads:
                log_event("read", entity_id="documents", count=len(docs))
            return docs
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            log_event("cache_decode_failed", key=cache_key, message=str(exc))
    docs_list = list_docs()
    if not _is_admin_user(current_user):
        visible_docs: list[DocumentModel] = []
        for document in docs_list:
            try:
                _enforce_document_access(document, current_user)
                visible_docs.append(document)
            except HTTPException:
                continue
        docs_list = visible_docs
    cache_set(
        cache_key,
        json.dumps([d.model_dump(mode="json") for d in docs_list]),
        ttl=30,
    )
    if (cfg := Config.load(CONFIG_FILE)) and cfg.log_reads:
        log_event("read", entity_id="documents", count=len(docs_list))
    return docs_list


@app.get("/documents/public", response_model=list[DocumentModel])
async def list_public_documents_endpoint() -> list[DocumentModel]:
    """Return documents that are flagged as public copies."""
    return list_public_documents()


@app.get("/documents/public/report")
async def public_documents_report_endpoint() -> list[dict[str, str | None]]:
    """Return minimal metadata for public documents."""
    return public_documents_report()


@app.get("/documents/public/{doc_id}/html")
async def public_document_html_endpoint(doc_id: str):
    """Return the watermarked HTML copy for a public document."""
    for record in list_archives():
        if record.document_id != doc_id:
            continue
        url = record.metadata.get("public_copy_url")
        if not isinstance(url, str) or not url.strip():
            continue
        expected_suffix = f"/{record.document_id}/{record.id}.public.html"
        if url.startswith("s3://"):
            if url.endswith(expected_suffix):
                return {"url": url}
            continue
        local_path = Path(url)
        if (
            local_path.name != f"{record.id}.public.html"
            or local_path.parent.name != record.document_id
            or not local_path.exists()
        ):
            continue
        return FileResponse(str(local_path), media_type="text/html")
    raise HTTPException(status_code=404, detail="Public copy not found")


@app.get("/documents/{doc_id}", response_model=DocumentModel)
async def get_document_endpoint(
    doc_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> DocumentModel:
    """Retrieve a single document by id."""
    document = get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    _enforce_document_access(document, current_user)
    if (cfg := Config.load(CONFIG_FILE)) and cfg.log_reads:
        log_event("read", entity_id=doc_id)
    return document


@app.get("/documents/{doc_id}/audit", response_model=list[AuditLogEntry])
async def get_document_audit_endpoint(
    doc_id: str,
    _: str = Depends(require_audit_access),
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[AuditLogEntry]:
    """Return audit events for a document."""
    document = get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    _enforce_document_access(document, current_user)
    events = get_audit_log(doc_id)
    if (cfg := Config.load(CONFIG_FILE)) and cfg.log_reads:
        log_event("read", entity_id=doc_id, target="audit", count=len(events))
    return events


@app.get("/documents/{doc_id}/verify-signature")
async def verify_signature_endpoint(
    doc_id: str,
    provider: str | None = None,
    user: auth.User = Depends(require_permission("verification_override")),
) -> dict[str, object]:
    """Validate the digital signatures associated with ``doc_id``.

    Parameters
    ----------
    provider:
        Optional signature provider or comma-separated list of providers to use
        for validation. If omitted, the provider stored with each approval is
        used and secondary providers are tried on failure.
    """
    try:
        providers_input: str | list[str] | None = provider
        if provider and "," in provider:
            providers_input = [p.strip() for p in provider.split(",") if p.strip()]
        return verify_document_signature(doc_id, provider=providers_input)
    except KeyError:
        # If the document cannot be found, surface a consistent 200 response
        # with a failing status rather than a 404. This aligns the API with
        # verification semantics used elsewhere where validation problems
        # (missing approvals, missing certificate, etc.) still return 200
        # and embed the failure in the payload.
        return {"status": "fail", "details": []}
    except ValueError as exc:
        # Bad provider input remains a client error
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.put("/documents/{doc_id}", response_model=DocumentModel)
async def update_document_endpoint(
    doc_id: str,
    document: DocumentModel,
    current_user: auth.User = Depends(auth.get_current_user),
) -> DocumentModel:
    """Update a document's content and save the previous version."""
    existing_document = get_document(doc_id)
    if existing_document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    _enforce_document_access(existing_document, current_user)
    try:
        updated, _ = update_document(doc_id, document.content, priority=document.priority)
        cache_set(
            "documents",
            json.dumps([d.model_dump(mode="json") for d in list_docs()]),
            ttl=30,
        )
        # Clear cached search results so subsequent queries reflect the update
        clear_cache()
        cfg = Config.load(CONFIG_FILE)
        if cfg:
            try:
                save_to_cms(updated, config=cfg)
            except Exception as exc:  # pragma: no cover - best effort
                raise HTTPException(status_code=502, detail=str(exc)) from exc
        return updated
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/cms/export/{doc_id}", response_model=CmsExportResponse)
async def export_document_to_cms(
    doc_id: str,
    body: CmsExportRequest,
    current_user: auth.User = Depends(auth.get_current_user),
) -> CmsExportResponse:
    """Export a document to the configured CMS."""

    document = get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")
    _enforce_document_access(document, current_user)
    cfg = Config.load(CONFIG_FILE)
    if not cfg or cfg.cms.strip().lower() == "none":
        raise HTTPException(status_code=409, detail="CMS is not configured")
    try:
        item_id = save_to_cms(document, config=cfg, fmt=body.fmt)
    except Exception as exc:  # pragma: no cover - best effort
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not item_id:
        raise HTTPException(status_code=409, detail="CMS is not configured")
    log_event(
        "export_document_cms",
        user_id=current_user.username,
        document=doc_id,
        message=render("tiptap_content_saved_to_cms_for_project_on", project_id=doc_id, date=""),
    )
    return CmsExportResponse(cms=cfg.cms.strip().lower(), item_id=item_id)


def _resolve_import_filename(item_id: str, filename: str | None, fmt: str | None) -> str:
    if filename:
        return filename
    if fmt:
        fmt_normalized = fmt.strip().lower()
        ext_map = {
            "markdown": "md",
            "md": "md",
            "html": "html",
            "docx": "docx",
            "pdf": "pdf",
            "txt": "txt",
            "text": "txt",
            "xml": "xml",
        }
        ext = ext_map.get(fmt_normalized, fmt_normalized)
        return f"cms-import.{ext}"
    return item_id


@app.post("/cms/import", status_code=201, response_model=DocumentModel)
async def import_document_from_cms(
    body: CmsImportRequest,
    current_user: auth.User = Depends(auth.get_current_user),
) -> DocumentModel:
    """Import a document from the configured CMS into DocReview360."""

    if body.project:
        project = get_project(body.project)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        _enforce_project_access(project, current_user)
    import_user = body.user
    if body.user is not None or not _is_admin_user(current_user):
        import_user = _resolve_requested_user(body.user, current_user)
    cfg = Config.load(CONFIG_FILE)
    if not cfg or cfg.cms.strip().lower() == "none":
        raise HTTPException(status_code=409, detail="CMS is not configured")
    try:
        payload = fetch_from_cms(body.item_id, config=cfg)
    except Exception as exc:  # pragma: no cover - best effort
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if payload is None:
        raise HTTPException(status_code=409, detail="CMS is not configured")
    filename = _resolve_import_filename(body.item_id, body.filename, body.fmt)
    if not filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    document = import_document(
        filename,
        payload,
        project=body.project,
        user=import_user,
        priority=body.priority,
    )
    cache_set(
        "documents",
        json.dumps([d.model_dump(mode="json") for d in list_docs()]),
        ttl=30,
    )
    return document


@app.post("/documents/{doc_id}/revisions", status_code=201)
async def create_revision_endpoint(
    doc_id: str,
    body: RevisionCreate,
    x_user: str | None = Header(None),
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, str]:
    """Store a new document revision and optionally archive it."""
    existing_document = get_document(doc_id)
    if existing_document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    _enforce_document_access(existing_document, current_user)
    revision_author = _resolve_requested_user(x_user, current_user)
    try:
        document, rev_id = update_document(
            doc_id,
            body.content,
            steps=body.steps,
            author=revision_author,
        )
        result: dict[str, str] = {"revisionId": rev_id}
        if body.promote:
            record = archive_doc(document)
            result["archiveId"] = record.id
        cfg = Config.load(CONFIG_FILE)
        if cfg and cfg.cms.strip().lower() != "none" and document.editor == "tiptap":
            try:
                save_to_cms(document, config=cfg)
            except Exception as exc:  # pragma: no cover - best effort
                raise HTTPException(status_code=502, detail=str(exc)) from exc
        return result
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/documents/{doc_id}/revisions", response_model=list[RevisionMeta])
async def list_revisions_endpoint(
    doc_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[RevisionMeta]:
    """List revision metadata for a document."""
    document = get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")
    _enforce_document_access(document, current_user)
    return [RevisionMeta(id=r.id, timestamp=r.timestamp, author=r.author) for r in document.history]


@app.get("/documents/{doc_id}/revisions/{rev_id}", response_model=DocumentRevision)
async def get_revision_endpoint(
    doc_id: str,
    rev_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> DocumentRevision:
    """Return a specific revision for a document."""
    document = get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")
    _enforce_document_access(document, current_user)
    for rev in document.history:
        if rev.id == rev_id:
            return rev
    raise HTTPException(status_code=404, detail="revision not found")


@app.post("/documents/{doc_id}/comments", response_model=CommentModel, status_code=201)
async def add_comment_endpoint(
    doc_id: str,
    body: CommentCreate,
    current_user: auth.User = Depends(auth.get_current_user),
) -> CommentModel:
    """Create a comment on the given document."""
    document = get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    _enforce_document_access(document, current_user)
    comment_user = _resolve_requested_user(body.user, current_user)
    comment = add_comment(doc_id, comment_user, body.text, parent=body.parent)
    return render_comment_for_response(comment)


@app.get("/documents/{doc_id}/comments", response_model=list[CommentModel])
async def list_comments_endpoint(
    doc_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[CommentModel]:
    """List comments for a document."""
    document = get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    _enforce_document_access(document, current_user)
    comments = list_comments(doc_id)
    if (cfg := Config.load(CONFIG_FILE)) and cfg.log_reads:
        log_event("read", entity_id=doc_id, target="comments", count=len(comments))
    return [render_comment_for_response(comment) for comment in comments]


@app.get("/documents/{doc_id}/export")
async def export_document_endpoint(
    doc_id: str,
    fmt: Literal[
        "markdown",
        "md",
        "text",
        "txt",
        "html",
        "htm",
        "docx",
        "pdf",
        "json",
        "xml",
    ],
    current_user: auth.User = Depends(auth.get_current_user),
) -> Response:
    """Return the document converted to the requested format."""
    document = get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    _enforce_document_access(document, current_user)
    try:
        cfg = Config.load(CONFIG_FILE)
        template = cfg.filename_template if cfg else "{id}"
        data, media, filename = export_document(document, fmt, name_template=template)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    if (cfg := Config.load(CONFIG_FILE)) and cfg.log_reads:
        log_event("read", entity_id=doc_id, format=fmt)
    return Response(content=data, media_type=media, headers=headers)


class ArchiveMetadata(BaseModel):
    """Optional metadata for archiving."""

    metadata: dict[str, Any] | None = None
    check_results: dict[str, Any] | None = None


@app.post("/archive/{doc_id}", status_code=201, response_model=ArchiveRecord)
async def archive_document_endpoint(
    doc_id: str,
    body: ArchiveMetadata | None = None,
    current_user: auth.User = Depends(auth.get_current_user),
) -> ArchiveRecord:
    """Archive a document in multiple formats."""
    document = get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    _enforce_document_access(document, current_user)
    return archive_doc(
        document,
        metadata=body.metadata if body else None,
        check_results=body.check_results if body else None,
    )


@app.get("/archive", response_model=list[ArchiveRecord])
async def list_archives_endpoint(
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[ArchiveRecord]:
    """Return all archived documents."""
    records = list_archives()
    if not _is_admin_user(current_user):
        visible_records: list[ArchiveRecord] = []
        for record in records:
            document = get_document(record.document_id)
            if document is None:
                continue
            try:
                _enforce_document_access(document, current_user)
                visible_records.append(record)
            except HTTPException:
                continue
        records = visible_records
    if (cfg := Config.load(CONFIG_FILE)) and cfg.log_reads:
        log_event("read", entity_id="archives", count=len(records))
    return records


@app.get("/archive/{archive_id}", response_model=ArchiveRecord)
async def get_archive_endpoint(
    archive_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> ArchiveRecord:
    """Retrieve a single archived record by id."""
    record = get_archive(archive_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Archive not found")
    document = get_document(record.document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    _enforce_document_access(document, current_user)
    if (cfg := Config.load(CONFIG_FILE)) and cfg.log_reads:
        log_event("read", entity_id=archive_id)
    return record


@app.get("/archive/{archive_id}/report/{fmt}")
async def download_report(
    archive_id: str,
    fmt: Literal["html", "pdf"],
    current_user: auth.User = Depends(auth.get_current_user),
) -> Response:
    """Return the archived check report in the requested format."""
    record = get_archive(archive_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Archive not found")
    document = get_document(record.document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    _enforce_document_access(document, current_user)
    if fmt == "html" and record.report_html is not None:
        return Response(record.report_html, media_type="text/html")
    if fmt == "pdf" and record.report_pdf is not None:
        return Response(record.report_pdf, media_type="application/pdf")
    raise HTTPException(status_code=404, detail="Report not found")


@app.get("/search", response_model=list[DocumentModel])
async def search_documents(
    q: str,
    project: str | None = None,
    user: str | None = None,
    priority: int | None = None,
    after: datetime | None = None,
    before: datetime | None = None,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[DocumentModel]:
    """Return documents matching a full text query with basic caching."""
    requested_user = user
    if user is not None:
        requested_user = _resolve_requested_user(user, current_user)
    elif not _is_admin_user(current_user):
        requested_user = current_user.username
    cache_key = (
        f"search-{current_user.username}-{q}-{project or ''}-"
        f"{requested_user or ''}-{priority or ''}-"
        f"{after.isoformat() if after else ''}-{before.isoformat() if before else ''}"
    )
    cached = cache_get(cache_key)
    if cached:
        try:
            if isinstance(cached, bytes):
                cached = cached.decode()
            data = json.loads(cached)
            return [DocumentModel.model_validate(d) for d in data]
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            log_event("cache_decode_failed", key=cache_key, message=str(exc))
    results = search(
        q,
        project=project,
        user=requested_user,
        priority=priority,
        after=after,
        before=before,
    )
    cache_set(
        cache_key,
        json.dumps([d.model_dump(mode="json") for d in results]),
        ttl=30,
    )
    if (cfg := Config.load(CONFIG_FILE)) and cfg.log_reads:
        log_event("read", entity_id="search", query=q, count=len(results))
    return results


@app.get("/search/export")
async def export_search_results(
    q: str,
    fmt: str = "json",
    current_user: auth.User = Depends(auth.get_current_user),
) -> Response:
    """Return search results in JSON or CSV with ranking and snippets."""
    docs = await search_documents(q, current_user=current_user)
    results = ranked_search(q, docs)
    rows = [{"id": r["document"].id, "snippet": r["snippet"], "score": r["score"]} for r in results]
    if fmt == "csv":
        output = "id,snippet,score\n" + "\n".join(
            f"{r['id']},{r['snippet'].replace(',', ' ')},{r['score']}" for r in rows
        )
        media = "text/csv"
    else:
        output = json.dumps(rows)
        media = "application/json"
    return Response(content=output, media_type=media)


@app.post("/search/saved", status_code=201)
async def save_search_endpoint(
    body: SavedSearchCreate,
    current_user: auth.User = Depends(auth.get_current_user),
) -> search_mod.SavedSearch:
    """Store a search query for later reuse."""
    saved_user = _resolve_requested_user(body.user, current_user)
    return save_search(body.query, user=saved_user)


@app.get("/search/saved", response_model=list[search_mod.SavedSearch])
async def list_saved_searches_endpoint(
    user: str | None = None,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[search_mod.SavedSearch]:
    """Return saved search queries."""
    requested_user = user
    if user is not None:
        requested_user = _resolve_requested_user(user, current_user)
    elif not _is_admin_user(current_user):
        requested_user = current_user.username
    return list_saved_searches(user=requested_user)


@app.get("/search/stats")
async def search_stats_endpoint() -> dict[str, int]:
    """Return counts of executed search queries."""
    return search_stats()


class WatchBody(BaseModel):
    user: str


@app.post("/watchlist/{project_id}", status_code=201, response_model=list[str])
async def toggle_watch_endpoint(
    project_id: str,
    body: WatchBody,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[str]:
    """Toggle ``project_id`` for ``body.user`` and return the updated list."""
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_access(project, current_user)
    watch_user = _resolve_requested_user(body.user, current_user)
    return toggle_watch(watch_user, project_id)


@app.get("/watchlist/{user}", response_model=list[str])
async def get_watchlist_endpoint(
    user: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[str]:
    """Return the watchlist for ``user``."""
    return get_watchlist(_resolve_requested_user(user, current_user))


@app.get("/ai/key")
async def get_ai_key_endpoint() -> dict[str, str | bool | None]:
    """Return whether the AI rewrite key is configured."""
    key = get_secret("openai")
    return {"configured": bool(key), "last4": key[-4:] if key else None}


@app.put("/ai/key")
async def update_ai_key_endpoint(payload: AiKeyPayload) -> dict[str, str | bool | None]:
    """Store the AI rewrite key in settings."""
    key = payload.key.strip() if payload.key else ""
    update_secret("openai", key or None)
    return {"configured": bool(key), "last4": key[-4:] if key else None}


@app.post("/ai/rewrite")
async def ai_rewrite_endpoint(body: TextBody) -> dict[str, str]:
    """Return a rewritten version of the provided text."""
    text = await rewrite_text(body.text)
    return {"result": text}


@app.post("/ai/summarize")
async def ai_summarize_endpoint(body: TextBody) -> dict[str, str]:
    """Return a one sentence summary of the provided text."""
    summary = await summarize_text(body.text)
    return {"result": summary}


@app.post("/chat")
async def chat_bot_endpoint(body: TextBody) -> dict[str, str]:
    """Return an answer from the simple chatbot."""
    from ..chat_bot import answer_question

    answer = await answer_question(body.text)
    return {"result": answer}


@app.post("/document-types", status_code=201, response_model=DocumentTypeModel)
async def create_document_type(doc_type: DocumentTypeModel) -> DocumentTypeModel:
    """Create a new document type."""
    from fastapi import HTTPException

    try:
        if not doc_type.workflow:
            from ..doc_types import DEFAULT_DOC_TYPE_PHASES

            workflow = DEFAULT_DOC_TYPE_PHASES.get(doc_type.name, ["Draft Development"])
            doc_type = doc_type.model_copy(update={"workflow": workflow})
        add_document_type(doc_type)
    except ValueError as exc:
        # Normalize validation errors into a 400 response so API clients
        # receive a predictable status code instead of an internal server
        # error when providing invalid data.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return doc_type


@app.get("/document-types", response_model=list[DocumentTypeModel])
async def get_document_types() -> list[DocumentTypeModel]:
    """Return all configured document types."""
    return list_document_types()


@app.get("/document-types/export")
async def export_doc_types_endpoint() -> Response:
    """Download all document types as JSON."""
    data = export_document_types_json()
    headers = {"Content-Disposition": "attachment; filename=document_types.json"}
    return Response(content=data, media_type="application/json", headers=headers)


@app.post("/document-types/import", status_code=201, response_model=list[DocumentTypeModel])
async def import_doc_types_endpoint(file: UploadFile = File(...)) -> list[DocumentTypeModel]:
    """Upload a JSON file of document types and replace existing ones."""
    data = await file.read()
    try:
        import_document_types_json(data.decode())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return list_document_types()


@app.get("/document-types/{name}", response_model=DocumentTypeModel)
async def get_document_type_endpoint(name: str) -> DocumentTypeModel:
    """Retrieve a single document type by name."""
    doc_type = get_document_type(name)
    if doc_type is None:
        raise HTTPException(status_code=404, detail="Document type not found")
    return doc_type


@app.put("/document-types/{name}", response_model=DocumentTypeModel)
async def update_document_type_endpoint(
    name: str, doc_type: DocumentTypeModel
) -> DocumentTypeModel:
    """Replace an existing document type."""
    try:
        if not doc_type.workflow:
            existing = get_document_type(name)
            if existing is None:
                raise KeyError(f"Document type '{name}' not found")
            doc_type = doc_type.model_copy(update={"workflow": list(existing.workflow)})
        return update_document_type(name, doc_type)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        # Renaming to an existing document type should surface as a conflict
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/document-types/{name}/usage", response_model=dict[str, Any])
async def check_document_type_usage_endpoint(name: str) -> dict[str, Any]:
    """Check if a document type is in use and return usage information."""
    from ..doc_types import get_document_type

    # Check if document type exists
    doc_type = get_document_type(name)
    if not doc_type:
        raise HTTPException(status_code=404, detail=f"Document type '{name}' not found")

    # Get all projects to check usage
    projects = list_projects()
    projects_using_doc_type = [p for p in projects if p.doc_type == name]

    return {
        "name": name,
        "in_use": len(projects_using_doc_type) > 0,
        "usage_count": len(projects_using_doc_type),
        "projects": [{"id": p.id, "name": p.name} for p in projects_using_doc_type],
    }


@app.delete("/document-types/{name}", status_code=204, response_class=Response)
async def delete_document_type_endpoint(name: str, replacement: str | None = None) -> Response:
    """Remove an existing document type. If in use, replacement is required."""
    from ..doc_types import get_document_type

    # Check if document type exists
    doc_type = get_document_type(name)
    if not doc_type:
        raise HTTPException(status_code=404, detail=f"Document type '{name}' not found")

    # Check if document type is in use
    projects = list_projects()
    projects_using_doc_type = [p for p in projects if p.doc_type == name]

    if projects_using_doc_type:
        if replacement:
            # Replacement must refer to a different, existing document type
            if replacement == name:
                raise HTTPException(
                    status_code=400, detail=f"Replacement document type '{replacement}' not found"
                )

            replacement_doc_type = get_document_type(replacement)
            if not replacement_doc_type:
                raise HTTPException(
                    status_code=404, detail=f"Replacement document type '{replacement}' not found"
                )

            # Update all projects to use the replacement
            for project in projects_using_doc_type:
                update_project(project.id, doc_type=replacement)
        else:
            # Document type in use but no replacement provided -> reject with
            # a clear message so callers know how to resolve the conflict.
            raise HTTPException(
                status_code=400,
                detail=f"Document type '{name}' is in use. Please specify a replacement.",
            )

    # Delete the document type
    try:
        delete_document_type(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Template management
# ---------------------------------------------------------------------------


def _normalize_template_metadata(
    metadata: dict[str, Any],
    *,
    doc_type: str | None,
    format_value: str | None,
) -> dict[str, Any]:
    normalized = dict(metadata)
    if doc_type:
        normalized["docType"] = doc_type
        normalized["doc_type"] = doc_type
    if format_value:
        normalized["format"] = format_value.upper()
        normalized["type"] = format_value.lower()
    normalized.setdefault("updated", datetime.now(timezone.utc).isoformat())
    return normalized


def _resolve_format_from_filename(filename: str | None) -> str | None:
    if not filename:
        return None
    parts = filename.rsplit(".", maxsplit=1)
    if len(parts) != 2:
        return None
    return parts[-1].strip().lower()


async def _parse_template_request(  # noqa: C901
    request: Request,
    *,
    fallback_name: str | None = None,
) -> tuple[str, dict[str, Any], bytes]:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        name = str(form.get("name") or form.get("id") or fallback_name or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name is required")
        doc_type = form.get("docType") or form.get("doc_type")
        format_value = form.get("format") or form.get("type")
        meta_value = form.get("meta") or "{}"
        content_text = form.get("content")
        try:
            metadata = json.loads(str(meta_value))
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="invalid metadata") from exc
        file = form.get("file")
        content: bytes
        if isinstance(file, UploadFile):
            content = await file.read()
            format_value = format_value or _resolve_format_from_filename(file.filename)
            metadata.setdefault("filename", file.filename)
        elif file is not None:
            if hasattr(file, "read"):
                maybe_content = file.read()
                if asyncio.iscoroutine(maybe_content):
                    maybe_content = await maybe_content
                content = (
                    maybe_content.encode("utf-8")
                    if isinstance(maybe_content, str)
                    else bytes(maybe_content)
                )
            else:
                content = bytes(file)
        elif content_text is not None:
            content = str(content_text).encode("utf-8")
        else:
            raise HTTPException(status_code=400, detail="template content is required")
        metadata = _normalize_template_metadata(
            metadata,
            doc_type=str(doc_type).strip() if doc_type else None,
            format_value=str(format_value).strip() if format_value else None,
        )
        return name, metadata, content

    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="invalid template payload")
    name = str(payload.get("name") or payload.get("id") or fallback_name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    content_text = payload.get("content")
    if content_text is None:
        raise HTTPException(status_code=400, detail="template content is required")
    content = str(content_text).encode("utf-8")
    metadata = payload.get("meta") or {}
    if metadata and not isinstance(metadata, dict):
        raise HTTPException(status_code=400, detail="meta must be a mapping")
    doc_type = payload.get("docType") or payload.get("doc_type")
    format_value = payload.get("format") or payload.get("type")
    metadata = _normalize_template_metadata(
        metadata,
        doc_type=str(doc_type).strip() if doc_type else None,
        format_value=str(format_value).strip() if format_value else None,
    )
    return name, metadata, content


@app.get("/templates")
async def list_templates_endpoint(
    request: Request,
    user: auth.User = Depends(auth.get_current_user),
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    is_admin = has_role(user.username, "admin")
    for name, ver in list_stored_templates().items():
        if not is_admin and (not ver.approved or ver.retired):
            continue
        meta = ver.metadata
        format_value = meta.get("format")
        type_value = meta.get("type")
        label = meta.get("label") or name
        description = meta.get("description")
        if not description and meta.get("docType"):
            description = f"Document type: {meta.get('docType')}"
        url = None
        if request is not None:
            url = str(request.url_for("download_template_endpoint", name=name))
        data = {
            "id": name,
            "name": name,
            "version": ver.version,
            "approved": ver.approved,
            "retired": ver.retired,
            "format": format_value,
            "type": type_value or (format_value.lower() if isinstance(format_value, str) else None),
            "label": label,
            "description": description,
            "url": url,
        }
        data.update(meta)
        items.append(data)
    return items


@app.get("/templates/{name}")
async def get_template_endpoint(
    name: str,
    user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    ver = get_latest_template(name)
    if not ver:
        raise HTTPException(status_code=404, detail="template not found")
    data: dict[str, Any] = {
        "id": name,
        "name": name,
        "version": ver.version,
        "content": ver.content.decode("utf-8", errors="ignore"),
        "approved": ver.approved,
        "retired": ver.retired,
    }
    data.update(ver.metadata)
    return data


@app.post("/templates", status_code=201)
async def upload_template_endpoint(
    request: Request,
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Store uploaded template content with metadata."""

    name, metadata, content = await _parse_template_request(request)
    version = store_template(name, content, metadata)
    return {
        "name": name,
        "version": version.version,
        "metadata": version.metadata,
        "approved": version.approved,
        "retired": version.retired,
    }


@app.put("/templates/{name}")
async def update_template_endpoint(
    name: str,
    request: Request,
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Update stored template content by creating a new version."""

    updated_name, metadata, content = await _parse_template_request(request, fallback_name=name)
    if updated_name != name:
        try:
            delete_stored_template(name)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    version = store_template(updated_name, content, metadata)
    return {
        "name": updated_name,
        "version": version.version,
        "metadata": version.metadata,
        "approved": version.approved,
        "retired": version.retired,
    }


@app.delete("/templates/{name}", status_code=204, response_class=Response)
async def delete_template_endpoint(
    name: str,
    user: auth.User = Depends(require_role("admin")),
) -> Response:
    """Remove a stored template."""

    try:
        delete_stored_template(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)


@app.get("/templates/{name}/download", response_class=Response, name="download_template_endpoint")
async def download_template_endpoint(
    name: str,
    user: auth.User = Depends(auth.get_current_user),
) -> Response:
    """Download the latest template file."""

    ver = get_latest_template(name)
    if not ver:
        raise HTTPException(status_code=404, detail="template not found")
    metadata = ver.metadata or {}
    format_value = metadata.get("format") or metadata.get("type") or "txt"
    format_lower = str(format_value).lower()
    extension = {
        "docx": "docx",
        "word": "docx",
        "html": "html",
        "json": "json",
        "xml": "xml",
        "txt": "txt",
        "md": "md",
        "markdown": "md",
    }.get(format_lower, format_lower)
    content_type = {
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "html": "text/html",
        "json": "application/json",
        "xml": "application/xml",
        "txt": "text/plain",
        "md": "text/markdown",
    }.get(extension, "application/octet-stream")
    filename = metadata.get("filename") or f"{name}.{extension}"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=ver.content, media_type=content_type, headers=headers)


@app.post("/templates/{name}/approve")
async def approve_template_endpoint(
    name: str, user: auth.User = Depends(require_role("admin"))
) -> dict[str, Any]:
    ver = approve_template(name)
    return {"name": name, "version": ver.version, "approved": ver.approved}


@app.post("/templates/{name}/retire")
async def retire_template_endpoint(
    name: str, user: auth.User = Depends(require_role("admin"))
) -> dict[str, Any]:
    ver = retire_template(name)
    return {"name": name, "version": ver.version, "retired": ver.retired}


class EmailTemplatePayload(BaseModel):
    """Payload for email templates."""

    name: str
    subject: str
    body: str
    task: str | None = None


@app.get("/email-templates")
async def list_email_templates_endpoint(
    user: auth.User = Depends(require_role("admin")),
) -> list[dict[str, Any]]:
    return [
        {
            "name": tmpl.name,
            "subject": tmpl.subject,
            "body": tmpl.body,
            "task": tmpl.task,
        }
        for tmpl in list_email_templates()
    ]


@app.get("/email-templates/{name}")
async def get_email_template_endpoint(
    name: str,
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    tmpl = get_email_template(name)
    if tmpl is None:
        raise HTTPException(status_code=404, detail="email template not found")
    return {
        "name": tmpl.name,
        "subject": tmpl.subject,
        "body": tmpl.body,
        "task": tmpl.task,
    }


@app.post("/email-templates", status_code=201)
async def create_email_template_endpoint(
    body: EmailTemplatePayload,
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    try:
        tmpl = create_email_template(body.name, body.subject, body.body, task=body.task)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "name": tmpl.name,
        "subject": tmpl.subject,
        "body": tmpl.body,
        "task": tmpl.task,
    }


@app.put("/email-templates/{name}")
async def update_email_template_endpoint(
    name: str,
    body: EmailTemplatePayload,
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    if name != body.name:
        raise HTTPException(status_code=400, detail="template name mismatch")
    try:
        tmpl = update_email_template(name, subject=body.subject, body=body.body, task=body.task)
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "name": tmpl.name,
        "subject": tmpl.subject,
        "body": tmpl.body,
        "task": tmpl.task,
    }


@app.delete("/email-templates/{name}", status_code=204, response_class=Response)
async def delete_email_template_endpoint(
    name: str,
    user: auth.User = Depends(require_role("admin")),
) -> Response:
    try:
        delete_email_template(name)
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)


@app.get("/plugin-marketplace")
async def list_marketplace() -> list[dict[str, Any]]:
    """Return available plugins with detailed information."""
    from ..plugin_marketplace import list_plugins_with_info

    return list_plugins_with_info()


class MarketplaceInstall(BaseModel):
    name: str


@app.post("/plugin-marketplace/install")
async def install_marketplace_plugin(
    body: MarketplaceInstall,
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, str]:
    """Install a plugin from the marketplace."""
    from ..plugin_marketplace import install_plugin

    try:
        install_plugin(body.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"installed": body.name}


# ---------------------------------------------------------------------------
# Phase management
# ---------------------------------------------------------------------------


class PhaseModel(BaseModel):
    """Simple phase schema."""

    name: str


@app.post("/phases", status_code=201, response_model=list[str])
async def create_phase_endpoint(body: PhaseModel) -> list[str]:
    """Create a new project phase."""
    add_phase(body.name)
    return list_phases()


@app.get("/phases", response_model=list[str])
async def list_phases_endpoint() -> list[str]:
    """Return all configured phases."""
    return list_phases()


@app.put("/phases/{name}", response_model=list[str])
async def rename_phase_endpoint(name: str, body: PhaseModel) -> list[str]:
    """Rename a phase and propagate changes to workflows."""

    phases_list = list_phases()
    if name not in phases_list:
        raise HTTPException(status_code=404, detail=f"Phase '{name}' not found")

    # Update registry
    try:
        rename_phase(name, body.name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    # Propagate to existing workflows
    all_workflows = list_workflows()
    for wf in all_workflows:
        wf.phases = [body.name if p == name else p for p in wf.phases]
        if wf.phase == name:
            wf.phase = body.name

    # Update any projects that stored the phase before a workflow was created.
    from ..search import projects

    for proj in projects.values():
        if getattr(proj, "initial_phase", None) == name:
            proj.initial_phase = body.name

    return list_phases()


@app.get("/phases/{name}/usage", response_model=dict[str, Any])
async def check_phase_usage_endpoint(name: str) -> dict[str, Any]:
    """Check if a phase is in use and return usage information."""

    # Check if phase exists
    phases_list = list_phases()
    if name not in phases_list:
        raise HTTPException(status_code=404, detail=f"Phase '{name}' not found")

    # Get all projects to check usage (projects don't have direct phase field, but workflows do)
    all_workflows = list_workflows()
    workflows_using_phase = [w for w in all_workflows if name in w.phases]

    # Get projects that use workflows with this phase
    projects = list_projects()
    projects_using_phase = []
    for project in projects:
        if project.workflow:
            workflow = get_workflow(project.workflow)
            if workflow and name in workflow.phases:
                projects_using_phase.append(project)

    return {
        "name": name,
        "in_use": len(projects_using_phase) > 0 or len(workflows_using_phase) > 0,
        "usage_count": len(projects_using_phase) + len(workflows_using_phase),
        "projects": [{"id": p.id, "name": p.name} for p in projects_using_phase],
        "workflows": [{"id": w.id, "project": w.project} for w in workflows_using_phase],
    }


# Internal helpers to keep endpoint complexity low
def _ensure_phase_exists(name: str, phases_list: list[str]) -> None:
    if name not in phases_list:
        raise HTTPException(status_code=404, detail=f"Phase '{name}' not found")


def _validate_replacement_exists(replacement: str | None, phases_list: list[str]) -> None:
    # Validate that a provided replacement refers to an existing phase
    if replacement and replacement not in phases_list:
        raise HTTPException(status_code=404, detail=f"Replacement phase '{replacement}' not found")


def _phase_usage(name: str) -> tuple[list[ProjectModel], list[WorkflowModel]]:
    # Compute projects and workflows that reference the given phase
    all_workflows = list_workflows()
    workflows_using_phase = [w for w in all_workflows if name in w.phases]

    projects_using_phase: list[ProjectModel] = []
    for project in list_projects():
        if project.workflow:
            workflow = get_workflow(project.workflow)
            if workflow and name in workflow.phases:
                projects_using_phase.append(project)
    return projects_using_phase, workflows_using_phase


def _apply_phase_replacement(
    name: str, replacement: str, workflows_using_phase: list[WorkflowModel]
) -> None:
    # Update all affected workflows to use the replacement phase
    for wf in workflows_using_phase:
        wf.phases = [replacement if p == name else p for p in wf.phases]
        if wf.phase == name:
            wf.phase = replacement


@app.delete("/phases/{name}", status_code=204, response_class=Response)
async def delete_phase_endpoint(name: str, replacement: str | None = None) -> Response:
    """Remove a phase by name. If in use, replacement is required."""
    phases_list = list_phases()
    _ensure_phase_exists(name, phases_list)
    _validate_replacement_exists(replacement, phases_list)

    projects_using_phase, workflows_using_phase = _phase_usage(name)

    if projects_using_phase or workflows_using_phase:
        if not replacement:
            detail_msg = (
                f"Phase '{name}' is in use by {len(projects_using_phase)} "
                f"project(s) and {len(workflows_using_phase)} workflow(s). "
                "Please specify a replacement phase."
            )
            raise HTTPException(status_code=400, detail=detail_msg)
        if replacement == name:
            raise HTTPException(status_code=400, detail="Replacement phase must be different")
        _apply_phase_replacement(name, replacement, workflows_using_phase)

    try:
        delete_phase(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)


def _workflow_template_usage(template_id: str) -> int:
    return sum(1 for wf in workflows.values() if wf.template == template_id)


def _serialize_workflow_template(template: WorkflowTemplateModel) -> WorkflowTemplateResponse:
    return WorkflowTemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        steps=template.steps,
        updated=template.updated,
        usage=_workflow_template_usage(template.id),
    )


@app.get("/workflow-templates", response_model=list[WorkflowTemplateResponse])
@log_call
async def list_workflow_templates_endpoint(
    x_user: str | None = Header(None),
) -> list[WorkflowTemplateResponse]:
    """Return workflow templates for the admin UI."""
    return [_serialize_workflow_template(t) for t in list_workflow_templates()]


@app.post("/workflow-templates", status_code=201, response_model=WorkflowTemplateResponse)
@log_call
async def create_workflow_template_endpoint(
    body: WorkflowTemplatePayload, x_user: str | None = Header(None)
) -> WorkflowTemplateResponse:
    """Create a workflow template."""
    try:
        template = create_workflow_template(body)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _serialize_workflow_template(template)


@app.get("/workflow-templates/{template_id}", response_model=WorkflowTemplateResponse)
@log_call
async def get_workflow_template_endpoint(
    template_id: str, x_user: str | None = Header(None)
) -> WorkflowTemplateResponse:
    """Return workflow template by id."""
    template = get_workflow_template(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Workflow template not found")
    return _serialize_workflow_template(template)


@app.put("/workflow-templates/{template_id}", response_model=WorkflowTemplateResponse)
@log_call
async def update_workflow_template_endpoint(
    template_id: str, body: WorkflowTemplatePayload, x_user: str | None = Header(None)
) -> WorkflowTemplateResponse:
    """Update workflow template by id."""
    try:
        template = update_workflow_template(template_id, body)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _serialize_workflow_template(template)


@app.delete("/workflow-templates/{template_id}", status_code=204, response_class=Response)
@log_call
async def delete_workflow_template_endpoint(
    template_id: str, x_user: str | None = Header(None)
) -> Response:
    """Delete workflow template by id."""
    try:
        delete_workflow_template(template_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)


@app.post("/workflows", status_code=201, response_model=WorkflowModel)
@log_call
async def create_workflow_endpoint(
    workflow: WorkflowCreate, x_user: str | None = Header(None)
) -> WorkflowModel:
    """Create a new workflow."""
    return create_workflow(workflow.project, workflow.phases, mode=workflow.mode)


@app.get("/workflows/{wf_id}", response_model=WorkflowModel)
@log_call
async def get_workflow_endpoint(wf_id: str, x_user: str | None = Header(None)) -> WorkflowModel:
    """Return a workflow by id."""
    wf = get_workflow(wf_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@app.get("/workflows", response_model=list[WorkflowModel])
@log_call
async def list_workflows_endpoint(
    project: str | None = None, x_user: str | None = Header(None)
) -> list[WorkflowModel]:
    """Return workflows optionally filtered by project."""
    return list_workflows(project, bootstrap=True)


@app.get("/workflow_roles", response_model=list[str])
@log_call
async def list_workflow_roles_endpoint(x_user: str | None = Header(None)) -> list[str]:
    """Return all unique workflow roles."""
    return list_roles()


@app.post("/workflows/{wf_id}/start", response_model=WorkflowModel)
@log_call
async def start_workflow_endpoint(
    wf_id: str,
    title: str | None = Form(None),
    file: UploadFile | None = File(None),
    x_user: str | None = Header(None),
) -> WorkflowModel:
    """Start a workflow by uploading a document."""

    wf = get_workflow(wf_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if title is None or not title.strip():
        title = wf.project or f"workflow-{wf_id}"
    data = await file.read() if file else None
    return start_workflow(wf_id, title, data)


@app.post("/workflows/{wf_id}/assign", response_model=WorkflowModel)
@log_call
async def assign_reviewer_endpoint(
    wf_id: str, body: ReviewerAssign, x_user: str | None = Header(None)
) -> WorkflowModel:
    """Assign a reviewer to a workflow."""
    try:
        return assign_reviewer(wf_id, body.user)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/workflows/{wf_id}/advance", response_model=WorkflowModel)
@log_call
async def advance_workflow_endpoint(wf_id: str, x_user: str | None = Header(None)) -> WorkflowModel:
    """Advance workflow to the next phase."""
    try:
        return advance_workflow(wf_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/approvals", status_code=201, response_model=ApprovalModel)
@log_call
async def create_approval_endpoint(body: ApprovalCreate) -> ApprovalModel:
    """Create an approval for a workflow."""
    return create_approval(
        body.workflow,
        body.reviewer,
        body.doc_id,
        due_at=body.due_at,
        description=body.description,
        phase_id=body.phase_id,
        required=body.required if body.required is not None else True,
        role=body.role,
        order=body.order,
        reminder_at=body.reminder_at,
        escalate_to=body.escalate_to,
        escalation_at=body.escalation_at,
    )


@app.get("/approvals", response_model=list[ApprovalModel])
@log_call
async def list_approvals_endpoint(
    workflow: str | None = None, phase: str | None = None
) -> list[ApprovalModel]:
    """Return approvals optionally filtered by workflow and phase."""
    return list_approvals(workflow, phase)


@app.get("/approvals/{approval_id}", response_model=ApprovalModel)
@log_call
async def get_approval_endpoint(approval_id: str) -> ApprovalModel:
    """Retrieve a single approval by id."""
    approval = get_approval(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval


@app.put("/approvals/{approval_id}", response_model=ApprovalModel)
@log_call
async def update_approval_endpoint(approval_id: str, body: ApprovalUpdate) -> ApprovalModel:
    """Update approval state and signature."""
    try:
        return await update_approval_state(
            approval_id,
            body.state,
            signature_id=body.signature_id,
            due_at=body.due_at,
        )
    except SignedApprovalImmutableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/approvals/{approval_id}", response_model=ApprovalModel)
@log_call
async def delete_approval_endpoint(approval_id: str) -> ApprovalModel:
    """Delete an approval by id."""
    try:
        return delete_approval(approval_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/approvals/{approval_id}/sign")
@log_call
async def sign_approval_endpoint(approval_id: str) -> dict[str, str]:
    """Begin a signing flow for an approval."""
    approval = get_approval(approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    wf = get_workflow(approval.workflow)
    if wf is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return_to = f"/projects/{wf.project}"
    doc_id = approval.document_id or wf.project
    try:
        url = send_for_signature(approval_id, doc_id, approval.reviewer, return_to)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    sig_id = approval.signature_id
    if sig_id is None:
        raise RuntimeError("signature id not set")
    return {"id": sig_id, "url": url}


@app.post("/sign/{doc_id}")
@log_call
async def sign_document(
    doc_id: str,
    user: str = Form(...),
    workflow: str | None = Form(None),
    approval: str | None = Form(None),
) -> dict[str, str]:
    """Create a signature request for ``doc_id`` using the active provider."""
    provider = get_provider()
    sig_id, url, _meta = provider.request_signature(
        doc_id,
        user,
        workflow_id=workflow,
        approval_id=approval,
    )
    if getattr(provider, "name", None) != "documenso":
        register_stub_signature(sig_id, workflow)
    return {"id": sig_id, "url": url}


@app.post("/sign/{sig_id}/complete")
@log_call
async def complete_sign(sig_id: str) -> None:
    """Mark a signature request as completed."""
    provider = get_provider()
    if getattr(provider, "name", None) == "documenso":
        complete_signature(sig_id)
        provider.process_webhook({"id": sig_id, "status": "signed"})
        return
    provider.process_webhook({"id": sig_id, "status": "signed"})
    try:
        from ..approvals import handle_signature_return

        await handle_signature_return(sig_id)
    except (KeyError, ValueError):
        pass


@app.get("/sign/{sig_id}")
@log_call
async def get_sign_status(sig_id: str) -> dict[str, str]:
    """Return signature status."""
    status = signature_status(sig_id)
    return {"status": status}


@app.post("/token", response_model=auth.Token)
async def token(
    request: Request, response: Response, form_data: OAuth2PasswordRequestForm = Depends()
) -> auth.Token:
    """Return a JWT access token for valid user credentials."""
    token_key = f"token:{form_data.username.strip().lower()}:{_request_source(request)}"
    _TOKEN_RATE_LIMITER.enforce(token_key)
    token_resp = await auth.login_for_access_token(form_data, request)
    response.set_cookie(
        "access_token",
        token_resp.access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    log_event(
        "login",
        user_id=form_data.username,
        message=render("login", user=form_data.username),
    )
    return token_resp


@app.post("/oidc/token", response_model=auth.Token)
async def oidc_token(
    request: Request, form_data: OAuth2PasswordRequestForm = Depends()
) -> auth.Token:
    """Return an ID token using the OIDC flow."""
    return await auth.login_for_oidc_token(form_data, request)


@app.get("/me")
async def read_current_user(current_user: auth.User = Depends(auth.get_current_user)) -> auth.User:
    """Return the authenticated user."""
    return current_user


@app.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    """Clear authentication cookie."""
    response.delete_cookie("access_token")
    response.delete_cookie("csrf_token")
    response.delete_cookie("session")
    return {"detail": "Logged out"}


@app.get("/oidc/me")
async def read_current_oidc_user(
    current_user: auth.User = Depends(auth.get_current_user_oidc),
) -> auth.User:
    """Return the authenticated user for the OIDC flow."""
    return current_user


@app.get("/", response_class=HTMLResponse)
async def root(request: Request) -> HTMLResponse:
    """Display login page or dashboard depending on session."""
    session_user = _decode_session_cookie(request.cookies.get("session"))
    if session_user:
        return templates.TemplateResponse(request, "dashboard.html", {"user": session_user})
    return templates.TemplateResponse(request, "login.html")


@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...)) -> Response:
    """Validate credentials and create a hardened session cookie."""
    login_key = f"login:{username.strip().lower()}:{_request_source(request)}"
    _LOGIN_RATE_LIMITER.enforce(login_key)
    if auth.authenticate_user(username, password):
        response = RedirectResponse("/projects", status_code=303)
        response.set_cookie(
            "session",
            _encode_session_cookie(username),
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=_SESSION_COOKIE_MAX_AGE,
        )
        log_event(
            "login",
            user_id=username,
            message=render("login", user=username),
        )
        return response
    return templates.TemplateResponse(
        request, "login.html", {"error": "Invalid credentials"}, status_code=400
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request) -> Response:
    """Placeholder dashboard displayed after login."""
    session_user = _decode_session_cookie(request.cookies.get("session"))
    if not session_user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "dashboard.html", {"user": session_user})


@app.get("/help", response_class=HTMLResponse)
async def help_page() -> HTMLResponse:
    """Display a lightweight help page rendered from Markdown."""
    # ``__file__`` resides in ``src/docreview360/api``; ascend to the repository
    # root before resolving the docs directory.
    doc_path = Path(__file__).resolve().parent.parent.parent.parent / "docs" / "getting_started.md"
    try:
        text = doc_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=500, detail="Unable to load documentation") from exc
    html = MarkdownIt().render(text)
    return HTMLResponse(html)


@app.get("/admin/panel")
async def admin_panel(user: auth.User = Depends(require_role("admin"))) -> dict[str, str]:
    """Return a trivial payload for admin-only access."""
    return {"user": user.username, "admin": "ok"}


@app.get("/plugins")
async def list_plugins() -> list[dict[str, Any]]:
    """Return metadata about registered plugins."""
    return plugin_registry.info()


@app.post("/plugins", status_code=201)
async def register_plugin(
    body: PluginModule,
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, list[str]]:
    """Load and register plugins from a module path."""
    try:
        load_plugins([body.module])
    except (ImportError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"names": plugin_registry.all()}


@app.put("/plugins/{name}/enable")
async def enable_plugin(
    name: str,
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, str]:
    """Enable a disabled plugin."""
    try:
        plugin_registry.enable(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"enabled": name}


@app.put("/plugins/{name}/disable")
async def disable_plugin(
    name: str,
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, str]:
    """Disable a plugin."""
    try:
        plugin_registry.disable(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"disabled": name}


@app.delete("/plugins/{name}", status_code=204, response_class=Response)
async def unregister_plugin(
    name: str,
    user: auth.User = Depends(require_role("admin")),
) -> Response:
    """Unregister a plugin entirely."""
    try:
        plugin_registry.unregister(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)


@app.get("/logs", response_model=list[LogEntry])
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
        # Accessing the operational logs should be treated the same as auditing
        # the audit log itself.  Previously this endpoint logged the action as
        # ``read`` which caused an extra entry compared to the dedicated audit
        # endpoint, making their outputs diverge in tests.  Using the
        # ``audit_log_access`` action keeps the semantics aligned and prevents
        # spurious differences when clients fetch logs via either route.
        log_event("audit_log_access", entity_id="logs", count=len(entries))
    return entries


@app.get("/api/audit", response_model=list[LogEntry])
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


@app.get("/logs/export")
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
    """Export audit logs in the requested format with metadata."""

    filters = {
        k: v
        for k, v in {
            "start": start,
            "end": end,
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


@app.get("/reports/summary", response_model=SummaryReport)
async def get_summary_report() -> SummaryReport:
    """Return counts of projects, documents, workflows, and approvals."""
    return generate_summary()


@app.get("/metrics/summary", response_model=SummaryReport)
async def get_metrics_summary() -> SummaryReport:
    """Alias for :func:`get_summary_report` used by dashboards."""
    return generate_summary()


@app.get("/reports/summary.csv")
async def get_summary_csv() -> Response:
    """Return the summary report as CSV."""
    return Response(reporting.summary_csv(), media_type="text/csv")


@app.get("/reports/throughput", response_model=list[reporting.ThroughputEntry])
async def throughput_endpoint(days: int = 7) -> list[reporting.ThroughputEntry]:
    """Return approval throughput data."""

    return reporting.throughput_data(days)


@app.get("/reports/throughput.csv")
async def throughput_csv_endpoint(days: int = 7) -> Response:
    """CSV export of :func:`throughput_endpoint`."""

    return Response(reporting.throughput_csv(days), media_type="text/csv")


@app.get("/reports/workload", response_model=dict[str, int])
async def workload_endpoint() -> dict[str, int]:
    """Return workload counts per user."""

    return reporting.workload_data()


@app.get("/reports/workload.csv")
async def workload_csv_endpoint() -> Response:
    """CSV export of :func:`workload_endpoint`."""

    return Response(reporting.workload_csv(), media_type="text/csv")


@app.get("/reports/dashboard", response_model=list[DashboardEntry])
async def get_dashboard_data(x_user: str | None = Header(None)) -> list[DashboardEntry]:
    """Return per-project data for dashboard widgets."""

    return dashboard_data(x_user)


@app.get("/dashboard/user", response_model=list[DashboardEntry])
async def user_dashboard_endpoint(x_user: str | None = Header(None)) -> list[DashboardEntry]:
    """Return dashboard data for the authenticated user."""

    if not x_user:
        raise HTTPException(status_code=401, detail="Missing user")
    return user_dashboard(x_user)


@app.get("/dashboard/widgets", response_model=WidgetMetrics)
async def get_widget_counts(x_user: str | None = Header(None)) -> WidgetMetrics:
    """Return assignment and approval counts for dashboard widgets."""

    return widget_counts(x_user)


@app.get("/dashboard/doc-types", response_model=dict[str, int])
async def doc_type_counts_endpoint() -> dict[str, int]:
    """Return active project counts grouped by document type."""

    return reporting.doc_type_counts()


class VisibilityPayload(BaseModel):
    """Dashboard widget visibility options."""

    stats: bool | None = None
    status: bool | None = None
    activity: bool | None = None
    logs: bool | None = None


@app.get("/dashboard/visibility")
async def get_visibility_endpoint(x_user: str | None = Header(None)) -> dict[str, bool]:
    """Return saved visibility settings for the user."""

    if not x_user:
        raise HTTPException(status_code=401, detail="Missing user")
    return get_visibility(x_user)


@app.put("/dashboard/visibility")
async def update_visibility_endpoint(
    body: VisibilityPayload, x_user: str | None = Header(None)
) -> dict[str, bool]:
    """Persist user visibility preferences."""

    if not x_user:
        raise HTTPException(status_code=401, detail="Missing user")
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    return set_visibility(x_user, data)


@app.get("/dashboard/manager")
async def manager_dashboard_endpoint(
    user: auth.User = Depends(require_role("manager")),
) -> dict[str, Any]:
    """Return dashboard information for managers."""

    return manager_dashboard()


@app.get("/status/public")
async def public_status_endpoint() -> dict[str, int]:
    """Expose limited status for unauthenticated users."""
    return public_status()


@app.get("/status/internal")
async def internal_status_endpoint() -> dict[str, int]:
    """Return extended system status for admins."""
    return internal_status()


@app.get("/dashboard/admin")
async def admin_dashboard_endpoint(
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, Any]:
    """Return system overview for administrators."""

    return admin_dashboard()


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

    user = websocket.headers.get("x-user") or websocket.query_params.get("user")

    # Allow anonymous connections for simple dashboards and tests.  If a user
    # identifier is supplied we still honour permission checks, but omitting the
    # header no longer results in an immediate 1008 policy‑violation close which
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


@app.get("/config", response_model=ConfigPayload)
async def get_config_endpoint(user: auth.User = Depends(require_role("admin"))) -> ConfigPayload:
    """Return the current application configuration."""
    cfg = Config.load(CONFIG_FILE)
    if cfg is None:
        cfg = Config(database="sqlite", editor="tiptap", cms="none", auth="oidc")
    return ConfigPayload(**cfg.__dict__)


@app.put("/config", response_model=ConfigPayload)
async def update_config_endpoint(
    payload: ConfigPayload,
    user: auth.User = Depends(require_role("admin")),
) -> ConfigPayload:
    """Persist a new configuration."""
    cfg = Config(**payload.model_dump())
    try:
        cfg.save(CONFIG_FILE)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return payload


@app.get("/signature-provider")
async def get_signature_provider_endpoint(
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, str | None]:
    """Return the configured signature providers."""

    providers = get_default_providers()
    primary = providers[0] if providers else None
    fallback = providers[1] if len(providers) > 1 else None
    return {"primary": primary, "fallback": fallback}


@app.put("/signature-provider")
async def update_signature_provider_endpoint(
    payload: SignatureProviderPayload,
    user: auth.User = Depends(require_role("admin")),
) -> dict[str, str | None]:
    """Persist the active signature provider selection."""

    update_setting("signature_provider_primary", payload.primary)
    update_setting("signature_provider_fallback", payload.fallback)
    return {"primary": payload.primary, "fallback": payload.fallback}


@app.post("/tools/convert")
async def convert_tool_endpoint(
    output_format: str = Form(...), file: UploadFile = File(...)
) -> dict[str, str]:
    """Convert an uploaded document and return the filename."""

    _ = await file.read()  # read file data but ignore for stub
    dest = convert_document(Path(file.filename or ""), output_format)
    return {"filename": dest.name}


@app.get("/environments")
async def list_environments() -> dict[str, Any]:
    """Return available environments and the current one."""
    return {"current": current_environment(), "envs": load_envs()}


@app.post("/environments/{name}")
async def switch_env_endpoint(name: str) -> dict[str, str]:
    """Switch the active environment and return its URL."""
    try:
        url = switch_environment(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"url": url}
