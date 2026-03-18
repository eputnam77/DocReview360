# SPDX-License-Identifier: MIT
"""Tools sub-router: /tools/*, /api-keys/*, /share-links/*, /share/*, /search/*,
/documents/preflight, /document-types/*, /watchlist/*, /ai/*, /chat."""
from __future__ import annotations

import json
import logging
import os
import secrets as _secrets_mod
from datetime import datetime
from typing import Any

import httpx
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from pydantic import BaseModel

from .. import auth
from ..accessibility import scan_document_accessibility, scan_result_to_dict
from ..ai_assist import rewrite_text, summarize_text
from ..cache import cache_get, cache_set
from ..config import CONFIG_FILE, Config
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
from ..doc_validation import preflight_validate as _preflight_validate
from ..document_converter import convert_document_content
from ..documents import DocumentModel
from ..fsv_proxy import (
    fsv_quality,
    fsv_regulatory_check,
    fsv_validate,
    get_fsv_url,
    is_fsv_configured,
)
from ..logs import log_event
from ..rbac import has_role, require_role
from ..search import (
    get_project,
    list_projects,
    list_saved_searches,
    ranked_search,
    save_search,
    search,
    search_stats,
    update_project,
)
from ..secrets import get_secret
from ..settings_manager import update_secret
from ..watchlist import get_watchlist, toggle_watch

_logger = logging.getLogger(__name__)

router = APIRouter()


class AccessibilityScanPayload(BaseModel):
    document_id: str
    content: str | None = None


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

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


def _request_source(request: Request) -> str:
    """Return a stable source identifier for request-scoped rate limiting."""
    forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded_for:
        return forwarded_for
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class AiKeyPayload(BaseModel):
    """Payload for storing the AI rewrite API key."""

    key: str | None = None


class TextBody(BaseModel):
    """Simple text payload for AI endpoints."""

    text: str


class SavedSearchCreate(BaseModel):
    """Input model for creating saved searches."""

    query: str
    user: str


class WatchBody(BaseModel):
    user: str


class _PreflightRequest(BaseModel):
    text: str
    min_reading_ease: float = 0.0
    require_no_undefined_acronyms: bool = False
    require_valid_headings: bool = True
    document_id: str | None = None  # Item 35: if provided, persists quality score


# ---------------------------------------------------------------------------
# AI routes
# ---------------------------------------------------------------------------

@router.get("/ai/key")
async def get_ai_key_endpoint(
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, str | bool | None]:
    """Return whether the AI rewrite key is configured."""
    key = get_secret("openai")
    return {"configured": bool(key), "last4": key[-4:] if key else None}


@router.put("/ai/key")
async def update_ai_key_endpoint(
    payload: AiKeyPayload,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, str | bool | None]:
    """Store the AI rewrite key in settings."""
    key = payload.key.strip() if payload.key else ""
    update_secret("openai", key or None)
    return {"configured": bool(key), "last4": key[-4:] if key else None}


@router.post("/ai/rewrite")
async def ai_rewrite_endpoint(
    body: TextBody,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, str]:
    """Return a rewritten version of the provided text."""
    text = await rewrite_text(body.text)
    return {"result": text}


@router.post("/ai/summarize")
async def ai_summarize_endpoint(
    body: TextBody,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, str]:
    """Return a one sentence summary of the provided text."""
    summary = await summarize_text(body.text)
    return {"result": summary}


@router.post("/chat")
async def chat_bot_endpoint(
    body: TextBody,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, str]:
    """Return an answer from the simple chatbot."""
    from ..chat_bot import answer_question
    answer = await answer_question(body.text)
    return {"result": answer}


# ---------------------------------------------------------------------------
# Document type routes
# ---------------------------------------------------------------------------

@router.post("/document-types", status_code=201, response_model=DocumentTypeModel)
async def create_document_type(
    doc_type: DocumentTypeModel,
    _user: auth.User = Depends(require_role("admin")),
) -> DocumentTypeModel:
    """Create a new document type (admin only)."""
    try:
        if not doc_type.workflow:
            from ..doc_types import DEFAULT_DOC_TYPE_PHASES
            workflow = DEFAULT_DOC_TYPE_PHASES.get(doc_type.name, ["Draft Development"])
            doc_type = doc_type.model_copy(update={"workflow": workflow})
        add_document_type(doc_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return doc_type


@router.get("/document-types", response_model=list[DocumentTypeModel])
async def get_document_types(
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[DocumentTypeModel]:
    """Return all configured document types."""
    return list_document_types()


@router.get("/document-types/export")
async def export_doc_types_endpoint(
    _user: auth.User = Depends(require_role("admin")),
) -> Response:
    """Download all document types as JSON (admin only)."""
    data = export_document_types_json()
    headers = {"Content-Disposition": "attachment; filename=document_types.json"}
    return Response(content=data, media_type="application/json", headers=headers)


@router.post("/document-types/import", status_code=201, response_model=list[DocumentTypeModel])
async def import_doc_types_endpoint(
    file: UploadFile = File(...),
    _user: auth.User = Depends(require_role("admin")),
) -> list[DocumentTypeModel]:
    """Upload a JSON file of document types and replace existing ones (admin only)."""
    data = await file.read()
    try:
        import_document_types_json(data.decode())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return list_document_types()


@router.get("/document-types/{name}", response_model=DocumentTypeModel)
async def get_document_type_endpoint(
    name: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> DocumentTypeModel:
    """Retrieve a single document type by name."""
    doc_type = get_document_type(name)
    if doc_type is None:
        raise HTTPException(status_code=404, detail="Document type not found")
    return doc_type


@router.put("/document-types/{name}", response_model=DocumentTypeModel)
async def update_document_type_endpoint(
    name: str,
    doc_type: DocumentTypeModel,
    _user: auth.User = Depends(require_role("admin")),
) -> DocumentTypeModel:
    """Replace an existing document type (admin only)."""
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
        raise HTTPException(status_code=409, detail=str(exc)) from exc


class _PhasesUpdateRequest(BaseModel):
    phases: list[str]


@router.get("/document-types/{name}/starter-content")
async def get_document_type_starter_content(
    name: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Return the curated starter HTML template for a document type.

    The frontend editor calls this endpoint when creating a new blank document
    to pre-populate the TipTap editor with section headings and placeholder text
    appropriate for the chosen document type.
    """
    doc_type = get_document_type(name)
    if doc_type is None:
        raise HTTPException(status_code=404, detail=f"Document type '{name}' not found")
    return {"doc_type": name, "content": doc_type.template or f"<h1>{name}</h1>"}


@router.get("/document-types/{name}/phases", response_model=list[str])
async def get_document_type_phases(
    name: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[str]:
    """Return the ordered list of workflow phases configured for a document type."""
    doc_type = get_document_type(name)
    if doc_type is None:
        raise HTTPException(status_code=404, detail=f"Document type '{name}' not found")
    return list(doc_type.workflow)


@router.put("/document-types/{name}/phases", response_model=DocumentTypeModel)
async def update_document_type_phases(
    name: str,
    body: _PhasesUpdateRequest,
    _user: auth.User = Depends(require_role("admin")),
) -> DocumentTypeModel:
    """Replace the workflow phases for a document type (admin only).

    Phases must be non-empty strings.  The order of the list defines the
    review progression for documents of this type.  Returns HTTP 404 if
    the document type does not exist and HTTP 422 on invalid phase data.
    """
    existing = get_document_type(name)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Document type '{name}' not found")
    if not body.phases:
        raise HTTPException(status_code=422, detail="phases must contain at least one entry")
    for phase in body.phases:
        if not isinstance(phase, str) or not phase.strip():
            raise HTTPException(status_code=422, detail="Each phase must be a non-empty string")
    updated = existing.model_copy(update={"workflow": body.phases})
    try:
        return update_document_type(name, updated)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/document-types/{name}/usage", response_model=dict[str, Any])
async def check_document_type_usage_endpoint(
    name: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Check if a document type is in use and return usage information."""
    doc_type = get_document_type(name)
    if not doc_type:
        raise HTTPException(status_code=404, detail=f"Document type '{name}' not found")

    projects = list_projects()
    projects_using_doc_type = [p for p in projects if p.doc_type == name]

    return {
        "name": name,
        "in_use": len(projects_using_doc_type) > 0,
        "usage_count": len(projects_using_doc_type),
        "projects": [{"id": p.id, "name": p.name} for p in projects_using_doc_type],
    }


@router.delete("/document-types/{name}", status_code=204, response_class=Response, response_model=None)
async def delete_document_type_endpoint(
    name: str,
    replacement: str | None = None,
    _user: auth.User = Depends(require_role("admin")),
) -> Response:
    """Remove an existing document type (admin only). If in use, replacement is required."""
    doc_type = get_document_type(name)
    if not doc_type:
        raise HTTPException(status_code=404, detail=f"Document type '{name}' not found")

    projects = list_projects()
    projects_using_doc_type = [p for p in projects if p.doc_type == name]

    if projects_using_doc_type:
        if replacement:
            if replacement == name:
                raise HTTPException(
                    status_code=400, detail=f"Replacement document type '{replacement}' not found"
                )
            replacement_doc_type = get_document_type(replacement)
            if not replacement_doc_type:
                raise HTTPException(
                    status_code=404, detail=f"Replacement document type '{replacement}' not found"
                )
            for project in projects_using_doc_type:
                update_project(project.id, doc_type=replacement)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Document type '{name}' is in use. Please specify a replacement.",
            )

    try:
        delete_document_type(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Search routes
# ---------------------------------------------------------------------------

@router.get("/search", response_model=list[DocumentModel])
async def search_documents(
    q: str,
    request: Request,
    project: str | None = None,
    user: str | None = None,
    priority: int | None = None,
    after: datetime | None = None,
    before: datetime | None = None,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[DocumentModel]:
    """Return documents matching a full text query with basic caching."""
    import docreview360.api as _api_mod
    _api_mod._SEARCH_RATE_LIMITER.enforce(f"search:{current_user.username}:{_request_source(request)}")
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


@router.get("/search/export")
async def export_search_results(
    q: str,
    fmt: str = "json",
    request: Request = None,
    current_user: auth.User = Depends(auth.get_current_user),
) -> Response:
    """Return search results in JSON or CSV with ranking and snippets."""
    docs = await search_documents(q, request=request, current_user=current_user)
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


@router.post("/search/saved", status_code=201)
async def save_search_endpoint(
    body: SavedSearchCreate,
    current_user: auth.User = Depends(auth.get_current_user),
) -> Any:
    """Store a search query for later reuse."""
    saved_user = _resolve_requested_user(body.user, current_user)
    return save_search(body.query, user=saved_user)


@router.get("/search/saved")
async def list_saved_searches_endpoint(
    user: str | None = None,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[Any]:
    """Return saved search queries."""
    requested_user = user
    if user is not None:
        requested_user = _resolve_requested_user(user, current_user)
    elif not _is_admin_user(current_user):
        requested_user = current_user.username
    return list_saved_searches(user=requested_user)


@router.get("/search/stats")
async def search_stats_endpoint(
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, int]:
    """Return counts of executed search queries."""
    return search_stats()


# ---------------------------------------------------------------------------
# Watchlist routes
# ---------------------------------------------------------------------------

@router.post("/watchlist/{project_id}", status_code=201, response_model=list[str])
async def toggle_watch_endpoint(
    project_id: str,
    body: WatchBody,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[str]:
    """Toggle ``project_id`` for ``body.user`` and return the updated list."""
    from .projects_router import _enforce_project_access
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    _enforce_project_access(project, current_user)
    watch_user = _resolve_requested_user(body.user, current_user)
    return toggle_watch(watch_user, project_id)


@router.get("/watchlist/{user}", response_model=list[str])
async def get_watchlist_endpoint(
    user: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[str]:
    """Return the watchlist for ``user``."""
    return get_watchlist(_resolve_requested_user(user, current_user))


# ---------------------------------------------------------------------------
# Tools routes
# ---------------------------------------------------------------------------

@router.post("/tools/convert")
async def convert_tool_endpoint(
    output_format: str = Form(...),
    file: UploadFile = File(...),
    current_user: auth.User = Depends(auth.get_current_user),
) -> Response:
    """Convert an uploaded document to the requested output format.

    Accepts DOCX, Markdown, HTML, plain text, or PDF uploads and returns the
    converted file as a downloadable response.  Supported output formats:
    ``markdown``, ``html``, ``txt``, ``docx``, ``word``.
    """
    data = await file.read()
    source_filename = file.filename or "document.txt"
    try:
        result = convert_document_content(data, source_filename, output_format)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    content: bytes = (
        result.content if isinstance(result.content, bytes)
        else result.content.encode("utf-8")
    )
    return Response(
        content=content,
        media_type=result.media_type,
        headers={"Content-Disposition": f'attachment; filename="{result.filename}"'},
    )


# ---------------------------------------------------------------------------
# Document preflight
# ---------------------------------------------------------------------------

@router.post("/documents/preflight")
async def document_preflight_endpoint(
    body: _PreflightRequest,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Run pre-flight checks on document text before phase advancement.

    When ``FEDERAL_STYLE_VALIDATOR_URL`` is configured the request is proxied
    to FSV and the FSV result is returned with ``"source": "fsv"``.  Otherwise
    the internal implementation is used and the result includes
    ``"source": "internal"``.
    """
    # --- FSV proxy path ---
    if is_fsv_configured():
        try:
            result_dict = await fsv_validate(body.text, doc_type=None)
            result_dict["source"] = "fsv"
            return result_dict
        except Exception as _exc:
            _logger.warning("FSV preflight proxy failed, falling back to internal: %s", _exc)
            # Fall through to internal implementation on proxy failure.

    # --- Internal implementation path ---
    result = _preflight_validate(
        body.text,
        min_reading_ease=body.min_reading_ease,
        require_no_undefined_acronyms=body.require_no_undefined_acronyms,
        require_valid_headings=body.require_valid_headings,
    )
    result_dict = result.to_dict()
    result_dict["source"] = "internal"

    # Item 35: persist quality score if a document_id was provided.
    if body.document_id:
        try:
            from ..doc_validation import score_plain_language
            from ..documents import update_document_quality_score
            from ..quality import quality_assessment

            qa = quality_assessment(body.text)
            pl = score_plain_language(body.text)
            from ..quality import QUALITY_FLAG_NAMES
            flags = dict(zip(QUALITY_FLAG_NAMES, qa.flags))
            update_document_quality_score(
                body.document_id,
                score=round(qa.score, 4),
                grade=pl.grade_level,
                flesch=pl.flesch_reading_ease,
                flags=flags,
            )
        except Exception as _exc:  # pragma: no cover - best-effort
            _logger.warning("preflight score persistence failed: %s", _exc)

    return result_dict


# ---------------------------------------------------------------------------
# Item 48 — Unified validation endpoint
# Consolidates /documents/preflight + /ai/regulatory-check + /ml/quality into
# a single round-trip so the frontend only needs to make one request.
# ---------------------------------------------------------------------------


class _UnifiedValidateRequest(BaseModel):
    text: str
    document_id: str | None = None
    min_reading_ease: float = 0.0
    require_no_undefined_acronyms: bool = False
    require_valid_headings: bool = False
    checks: list[str] = []
    """Optional subset of checks to run. Empty list = all checks.
    Supported values: ``preflight``, ``regulatory``, ``quality``.
    Use this to skip checks that don't apply to a given document type."""


@router.post("/documents/validate")
async def unified_validate_endpoint(
    body: _UnifiedValidateRequest,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Run all three validation passes in one request and return categorised results.

    Replaces three separate parallel calls to ``/documents/preflight``,
    ``/ai/regulatory-check``, and ``/ml/quality``.  The response shape is::

        {
          "preflight": { ...preflight result... },
          "regulatory": { ...regulatory result... },
          "quality": { ...quality result... },
          "source": "fsv" | "internal",
          "checks_run": ["preflight", "regulatory", "quality"]
        }

    Pass ``checks`` to run only a subset, e.g. ``["preflight"]`` for document
    types where regulatory or quality checks don't apply.
    """
    import asyncio

    run_all = not body.checks
    run_preflight = run_all or "preflight" in body.checks
    run_regulatory = run_all or "regulatory" in body.checks
    run_quality = run_all or "quality" in body.checks

    checks_run: list[str] = []

    async def _run_preflight() -> dict[str, Any]:
        if not run_preflight:
            return {}
        # Reuse existing logic by calling the same functions
        if is_fsv_configured():
            try:
                result = await fsv_validate(body.text, doc_type=None)
                result["source"] = "fsv"
                checks_run.append("preflight")
                return result
            except Exception as _exc:
                _logger.warning("FSV preflight failed in unified: %s", _exc)
        result = _preflight_validate(
            body.text,
            min_reading_ease=body.min_reading_ease,
            require_no_undefined_acronyms=body.require_no_undefined_acronyms,
            require_valid_headings=body.require_valid_headings,
        ).to_dict()
        result["source"] = "internal"
        checks_run.append("preflight")
        if body.document_id:
            try:
                from ..doc_validation import score_plain_language
                from ..documents import update_document_quality_score
                from ..quality import QUALITY_FLAG_NAMES, quality_assessment
                qa = quality_assessment(body.text)
                pl = score_plain_language(body.text)
                flags = dict(zip(QUALITY_FLAG_NAMES, qa.flags))
                update_document_quality_score(
                    body.document_id, score=round(qa.score, 4),
                    grade=pl.grade_level, flesch=pl.flesch_reading_ease, flags=flags,
                )
            except Exception:  # pragma: no cover - best-effort
                pass
        return result

    async def _run_regulatory() -> dict[str, Any]:
        if not run_regulatory:
            return {}
        if is_fsv_configured():
            try:
                r = await fsv_regulatory_check(body.text)
                checks_run.append("regulatory")
                return r
            except Exception as _exc:
                _logger.warning("FSV regulatory failed in unified: %s", _exc)
        from ..regulatory import check_regulatory_citations
        citation_results = check_regulatory_citations(body.text)
        checks_run.append("regulatory")
        return {
            "citations_found": len(citation_results),
            "results": [
                {"citation": r.citation, "valid_format": r.valid_format,
                 "known": r.known, "issues": r.issues}
                for r in citation_results
            ],
            "has_issues": any(r.issues for r in citation_results),
        }

    async def _run_quality() -> dict[str, Any]:
        if not run_quality:
            return {}
        if is_fsv_configured():
            try:
                r = await fsv_quality(body.text, document_id=body.document_id)
                checks_run.append("quality")
                return r
            except Exception as _exc:
                _logger.warning("FSV quality failed in unified: %s", _exc)
        from ..doc_validation import score_plain_language
        from ..quality import quality_assessment
        qa = quality_assessment(body.text)
        pl = score_plain_language(body.text)
        checks_run.append("quality")
        return {
            "score": round(qa.score, 4),
            "raw_score": round(qa.score, 4),
            "plain_language_grade": pl.grade_level,
            "flesch_reading_ease": pl.flesch_reading_ease,
            "source": "internal",
        }

    preflight_result, regulatory_result, quality_result = await asyncio.gather(
        _run_preflight(), _run_regulatory(), _run_quality()
    )

    overall_source = "fsv" if is_fsv_configured() else "internal"
    return {
        "preflight": preflight_result,
        "regulatory": regulatory_result,
        "quality": quality_result,
        "source": overall_source,
        "checks_run": checks_run,
    }


# ---------------------------------------------------------------------------
# API key management
# ---------------------------------------------------------------------------

from docreview360 import api_keys as _api_keys_mod  # noqa: E402


class _APIKeyCreateRequest(BaseModel):
    name: str
    scopes: list[str] = []
    expires_at: str | None = None


class _APIKeyResponse(BaseModel):
    id: str
    owner: str
    name: str
    prefix: str
    created_at: str
    expires_at: str | None = None
    last_used_at: str | None = None
    is_active: bool
    scopes: list[str]
    key: str | None = None  # only on create


@router.post("/api-keys", response_model=_APIKeyResponse, status_code=201)
async def create_api_key(
    body: _APIKeyCreateRequest,
    current_user: auth.User = Depends(auth.get_current_user),
) -> Any:
    """Create a new API key for the authenticated user."""
    expires_at = None
    if body.expires_at:
        try:
            expires_at = datetime.fromisoformat(body.expires_at)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid expires_at format") from exc
    record = _api_keys_mod.create_api_key(
        current_user.username,
        body.name,
        scopes=body.scopes,
        expires_at=expires_at,
    )
    return record


@router.get("/api-keys", response_model=list[_APIKeyResponse])
async def list_api_keys(current_user: auth.User = Depends(auth.get_current_user)) -> Any:
    """List all API keys owned by the authenticated user."""
    return _api_keys_mod.list_api_keys(current_user.username)


@router.get("/api-keys/{key_id}", response_model=_APIKeyResponse)
async def get_api_key(
    key_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> Any:
    """Retrieve metadata for a single API key."""
    record = _api_keys_mod.get_api_key(key_id, current_user.username)
    if record is None:
        raise HTTPException(status_code=404, detail="API key not found")
    return record


@router.delete("/api-keys/{key_id}", status_code=204, response_class=Response, response_model=None)
async def revoke_api_key(
    key_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> Response:
    """Revoke an API key owned by the authenticated user."""
    ok = _api_keys_mod.revoke_api_key(key_id, current_user.username)
    if not ok:
        raise HTTPException(status_code=404, detail="API key not found")
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Share links
# ---------------------------------------------------------------------------

_share_links: dict[str, dict[str, Any]] = {}  # token → record


class _ShareLinkCreateRequest(BaseModel):
    resource_type: str  # "project" | "document"
    resource_id: str
    permission: str = "read"  # "read" | "comment"
    expires_at: str | None = None


class _ShareLinkResponse(BaseModel):
    id: str
    resource_type: str
    resource_id: str
    token: str
    created_by: str
    created_at: str
    expires_at: str | None = None
    permission: str
    is_active: bool
    url: str


def _make_share_url(token: str) -> str:
    base = os.getenv("DOCREVIEW360_PUBLIC_URL", "http://localhost:8000")
    return f"{base}/share/{token}"


@router.post("/share-links", response_model=_ShareLinkResponse, status_code=201)
async def create_share_link(
    body: _ShareLinkCreateRequest,
    current_user: auth.User = Depends(auth.get_current_user),
) -> Any:
    """Create a shareable link for a project or document."""
    from datetime import timezone as _tz

    if body.resource_type not in ("project", "document"):
        raise HTTPException(status_code=422, detail="resource_type must be 'project' or 'document'")
    if body.permission not in ("read", "comment"):
        raise HTTPException(status_code=422, detail="permission must be 'read' or 'comment'")

    expires_at = None
    if body.expires_at:
        try:
            expires_at = datetime.fromisoformat(body.expires_at)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid expires_at format") from exc

    token = _secrets_mod.token_urlsafe(24)
    link_id = _secrets_mod.token_hex(16)
    now = datetime.now(tz=_tz.utc)

    record: dict[str, Any] = {
        "id": link_id,
        "resource_type": body.resource_type,
        "resource_id": body.resource_id,
        "token": token,
        "created_by": current_user.username,
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat() if expires_at else None,
        "permission": body.permission,
        "is_active": True,
        "url": _make_share_url(token),
    }
    _share_links[token] = record
    return record


@router.get("/share-links/{link_id}", response_model=_ShareLinkResponse)
async def get_share_link(
    link_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> Any:
    """Get metadata for a share link by ID."""
    for record in _share_links.values():
        if record["id"] == link_id and record["created_by"] == current_user.username:
            return record
    raise HTTPException(status_code=404, detail="Share link not found")


@router.delete("/share-links/{link_id}", status_code=204, response_class=Response, response_model=None)
async def revoke_share_link(
    link_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> Response:
    """Revoke a share link."""
    for record in _share_links.values():
        if record["id"] == link_id and record["created_by"] == current_user.username:
            record["is_active"] = False
            return Response(status_code=204)
    raise HTTPException(status_code=404, detail="Share link not found")


@router.get("/share/{token}")
async def resolve_share_link(token: str) -> Any:
    """Public endpoint: resolve a share token to the underlying resource."""
    from datetime import timezone as _tz

    record = _share_links.get(token)
    if record is None or not record["is_active"]:
        raise HTTPException(status_code=404, detail="Share link not found or expired")
    if record["expires_at"] is not None:
        exp = datetime.fromisoformat(record["expires_at"])
        if datetime.now(tz=_tz.utc) > exp:
            raise HTTPException(status_code=410, detail="Share link has expired")
    return {
        "resource_type": record["resource_type"],
        "resource_id": record["resource_id"],
        "permission": record["permission"],
    }


# ---------------------------------------------------------------------------
# Regulatory citation checker (AI-Assisted Review)
# ---------------------------------------------------------------------------


class _RegulatoryCheckRequest(BaseModel):
    text: str


class _RegulatoryCheckResponse(BaseModel):
    citations_found: int
    results: list[dict[str, object]]
    has_issues: bool


@router.post("/ai/regulatory-check", response_model=_RegulatoryCheckResponse)
async def regulatory_check(
    body: _RegulatoryCheckRequest,
    current_user: auth.User = Depends(auth.get_current_user),
) -> _RegulatoryCheckResponse:
    """Check regulatory citations in ``text`` for format correctness and catalog membership.

    Extracts citations matching known regulatory schemas (21 CFR, ISO, IEC, EU MDR/IVDR)
    and reports format validity, catalog membership, and any issues found.
    Returns HTTP 422 when ``text`` is empty.

    When ``FEDERAL_STYLE_VALIDATOR_URL`` is configured the request is proxied
    to FSV's ``/regulatory-check`` endpoint and the result is returned directly.
    Otherwise the internal ``regulatory.py`` implementation is used.
    """
    if not body.text.strip():
        raise HTTPException(status_code=422, detail="text is required")

    # --- FSV proxy path ---
    if is_fsv_configured():
        try:
            fsv_result = await fsv_regulatory_check(body.text)
            # Normalise to _RegulatoryCheckResponse shape; FSV may return the
            # same shape but we guard against missing keys defensively.
            return _RegulatoryCheckResponse(
                citations_found=int(fsv_result.get("citations_found", 0)),
                results=list(fsv_result.get("results", [])),
                has_issues=bool(fsv_result.get("has_issues", False)),
            )
        except Exception as _exc:
            _logger.warning(
                "FSV regulatory-check proxy failed, falling back to internal: %s", _exc
            )
            # Fall through to internal implementation on proxy failure.

    # --- Internal implementation path ---
    from ..regulatory import check_regulatory_citations

    citation_results = check_regulatory_citations(body.text)
    serialized: list[dict[str, object]] = [
        {
            "citation": r.citation,
            "valid_format": r.valid_format,
            "known": r.known,
            "issues": r.issues,
        }
        for r in citation_results
    ]
    return _RegulatoryCheckResponse(
        citations_found=len(citation_results),
        results=serialized,
        has_issues=any(r.issues for r in citation_results),
    )


# ---------------------------------------------------------------------------
# FSV status
# ---------------------------------------------------------------------------


@router.get("/fsv/status")
async def fsv_status_endpoint(
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Return whether the Federal Style Validator (FSV) integration is active.

    Response fields:
    - ``configured``: ``true`` when ``FEDERAL_STYLE_VALIDATOR_URL`` is set.
    - ``url``: the configured base URL, or ``null``.
    - ``reachable``: ``true`` when a ``GET {url}/health`` probe succeeds within
      2 seconds.  Always ``false`` when not configured.
    """
    fsv_url = get_fsv_url()
    configured = bool(fsv_url)
    reachable = False
    if configured and fsv_url:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{fsv_url.rstrip('/')}/health")
                reachable = resp.is_success
        except Exception:
            reachable = False
    return {"configured": configured, "url": fsv_url, "reachable": reachable}


@router.post("/tools/accessibility-scan")
async def accessibility_scan(
    payload: AccessibilityScanPayload,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict:
    """Scan a document's content for WCAG 2.1 AA / Section 508 accessibility issues.

    Pass either ``content`` (raw HTML/text) or a ``document_id`` to load content
    from the database.  Returns a scan result with violations, passes, and a score.
    """
    content = payload.content or ""
    if not content and payload.document_id:
        # Attempt to load from DB
        try:
            from ..documents import get_document  # type: ignore[import]

            doc = get_document(payload.document_id)
            content = getattr(doc, "content", "") or getattr(doc, "text", "") or ""
        except Exception:
            pass

    result = scan_document_accessibility(content, doc_id=payload.document_id)
    return scan_result_to_dict(result)
