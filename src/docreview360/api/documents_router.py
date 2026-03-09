"""Documents sub-router: /documents/*, /cms/*, /sign/* routes."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Body, Depends, File, Form, Header, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .. import auth
from ..rbac import has_role, require_permission
from ..approvals import (
    SignedApprovalImmutableError,
    get_approval,
    send_for_signature,
    update_approval_state,
)
from ..archive import (
    ArchiveRecord,
    archive_document as archive_doc,
    get_archive,
    list_archives,
)
from ..audit import AuditLogEntry, get_audit_log, log_audit_event
from ..cache import cache_get, cache_set, clear_cache
from ..cms import fetch_from_cms, save_to_cms
from ..comments import CommentModel, add_comment, list_comments, render_comment_for_response, update_comment
from ..config import CONFIG_FILE, Config
from ..documenso import (
    complete_signature,
    register_stub_signature,
    signature_status,
)
from ..documents import (
    DocumentModel,
    FrozenDocumentError,
    get_document,
    get_version_history,
    freeze_document,
    unfreeze_document,
    restore_document_version,
    diff_document_revisions,
    import_document,
    list_public_documents,
    public_documents_report,
    update_document,
    DocumentRevision,
)
from ..documents import list_documents as list_docs
from ..exporter import export_document
from ..integrations.signature import get_provider
from ..logs import log_event
from ..search import get_project
from ..approvals import verify_document_signature

_logger = logging.getLogger(__name__)

router = APIRouter()


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


def _request_source(request: Request) -> str:
    """Return a stable source identifier for request-scoped rate limiting."""
    forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded_for:
        return forwarded_for
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def require_audit_access(current_user: auth.User = Depends(auth.get_current_user)) -> str:
    """Ensure the requester may view audit logs and record the attempt."""
    from ..rbac import has_permission
    if has_permission(current_user.username, "view_audit_log"):
        log_event("audit_log_access", user_id=current_user.username, status="success")
        return current_user.username
    log_event("audit_log_access", user_id=current_user.username, status="denied")
    raise HTTPException(status_code=403, detail="Forbidden")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class RevisionCreate(BaseModel):
    """Payload for creating a document revision."""

    content: str
    steps: list[Any] | None = None
    promote: bool = False


class RevisionMeta(BaseModel):
    """Metadata for a document revision."""

    id: str
    timestamp: datetime
    author: str


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


class ArchiveMetadata(BaseModel):
    """Optional metadata for archiving."""

    metadata: dict[str, Any] | None = None
    check_results: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Document routes
# ---------------------------------------------------------------------------

@router.post("/documents/import", status_code=201, response_model=DocumentModel)
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
    import docreview360.api as _api_mod
    _api_mod._UPLOAD_RATE_LIMITER.enforce(f"documents-import:{current_user.username}:{_request_source(request)}")

    if project:
        project_model = get_project(project)
        if project_model is None:
            raise HTTPException(status_code=404, detail="Project not found")
        from ..search import get_project as _get_project
        from .projects_router import _enforce_project_access
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
    from ..messages import render
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


@router.post("/documents/tiptap", status_code=201, response_model=DocumentModel)
async def import_tiptap_endpoint(
    body: dict[str, Any],
    link_duplicates: bool = Query(False),
    current_user: auth.User = Depends(auth.get_current_user),
) -> DocumentModel:
    """Import a TipTap JSON document."""
    from ..tiptap import import_tiptap_document
    from ..messages import render

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


@router.get("/documents", response_model=list[DocumentModel])
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


@router.get("/documents/public", response_model=list[DocumentModel])
async def list_public_documents_endpoint() -> list[DocumentModel]:
    """Return documents that are flagged as public copies."""
    return list_public_documents()


@router.get("/documents/public/report")
async def public_documents_report_endpoint() -> list[dict[str, str | None]]:
    """Return minimal metadata for public documents."""
    return public_documents_report()


@router.get("/documents/public/{doc_id}/html")
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


@router.get("/documents/{doc_id}", response_model=DocumentModel)
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


@router.get("/documents/{doc_id}/audit", response_model=list[AuditLogEntry])
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


@router.get("/documents/{doc_id}/audit/export", response_model=dict[str, Any])
async def export_document_audit_endpoint(
    doc_id: str,
    _: str = Depends(require_audit_access),
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, Any]:
    """Export all audit events for a document as a structured JSON package."""
    document = get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    _enforce_document_access(document, current_user)
    events = get_audit_log(doc_id)
    from datetime import datetime, timezone

    event_counts: dict[str, int] = {}
    for ev in events:
        event_counts[ev.event] = event_counts.get(ev.event, 0) + 1

    return {
        "document_id": doc_id,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "exported_by": current_user.username,
        "total_events": len(events),
        "event_summary": event_counts,
        "events": [ev.model_dump(mode="json") for ev in events],
    }


@router.get("/documents/{doc_id}/audit/snapshots", response_model=list[AuditLogEntry])
async def list_phase_snapshots_endpoint(
    doc_id: str,
    _: str = Depends(require_audit_access),
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[AuditLogEntry]:
    """Return phase-transition snapshots recorded for a document."""
    document = get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    _enforce_document_access(document, current_user)
    from ..audit_snapshots import get_phase_snapshots
    return get_phase_snapshots(doc_id)


@router.post("/documents/{doc_id}/audit/snapshots", response_model=AuditLogEntry)
async def create_phase_snapshot_endpoint(
    doc_id: str,
    phase: str = Body(..., embed=True),
    previous_phase: str | None = Body(default=None, embed=True),
    current_user: auth.User = Depends(require_permission("update")),
) -> AuditLogEntry:
    """Capture a phase-transition snapshot for a document."""
    document = get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    from ..audit_snapshots import capture_phase_snapshot
    return capture_phase_snapshot(
        doc_id,
        phase,
        actor=current_user.username,
        previous_phase=previous_phase,
    )


@router.get("/documents/{doc_id}/verify-signature")
async def verify_signature_endpoint(
    doc_id: str,
    provider: str | None = None,
    user: auth.User = Depends(require_permission("verification_override")),
) -> dict[str, object]:
    """Validate the digital signatures associated with ``doc_id``."""
    log_event(
        "verification_override",
        user_id=user.username,
        entity_id=doc_id,
        provider=provider or "auto",
    )
    try:
        providers_input: str | list[str] | None = provider
        if provider and "," in provider:
            providers_input = [p.strip() for p in provider.split(",") if p.strip()]
        return verify_document_signature(doc_id, provider=providers_input)
    except KeyError:
        return {"status": "fail", "details": []}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/documents/{doc_id}", response_model=DocumentModel)
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


# ---------------------------------------------------------------------------
# CMS routes
# ---------------------------------------------------------------------------

@router.post("/cms/export/{doc_id}", response_model=CmsExportResponse)
async def export_document_to_cms(
    doc_id: str,
    body: CmsExportRequest,
    current_user: auth.User = Depends(auth.get_current_user),
) -> CmsExportResponse:
    """Export a document to the configured CMS."""
    from ..messages import render
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


@router.post("/cms/import", status_code=201, response_model=DocumentModel)
async def import_document_from_cms(
    body: CmsImportRequest,
    current_user: auth.User = Depends(auth.get_current_user),
) -> DocumentModel:
    """Import a document from the configured CMS into DocReview360."""
    from .projects_router import _enforce_project_access

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


# ---------------------------------------------------------------------------
# Revision routes
# ---------------------------------------------------------------------------

@router.post("/documents/{doc_id}/revisions", status_code=201)
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


@router.get("/documents/{doc_id}/revisions", response_model=list[RevisionMeta])
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


@router.get("/documents/{doc_id}/revisions/{rev_id}", response_model=DocumentRevision)
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


# ---------------------------------------------------------------------------
# Comment routes
# ---------------------------------------------------------------------------

@router.post("/documents/{doc_id}/comments", response_model=CommentModel, status_code=201)
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
    comment = add_comment(doc_id, comment_user, body.text, parent=body.parent, tags=body.tags)
    return render_comment_for_response(comment)


@router.get("/documents/{doc_id}/comments", response_model=list[CommentModel])
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


@router.put("/documents/{doc_id}/comments/{comment_id}", response_model=CommentModel)
async def update_comment_endpoint(
    doc_id: str,
    comment_id: str,
    body: CommentUpdate,
    current_user: auth.User = Depends(auth.get_current_user),
) -> CommentModel:
    """Update status, text, or tags for an existing comment."""
    document = get_document(doc_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    _enforce_document_access(document, current_user)
    try:
        comment = update_comment(
            doc_id,
            comment_id,
            status=body.status,
            text=body.text,
            tags=body.tags,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return render_comment_for_response(comment)


# ---------------------------------------------------------------------------
# Export route
# ---------------------------------------------------------------------------

@router.get("/documents/{doc_id}/export")
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
    request: Request,
    current_user: auth.User = Depends(auth.get_current_user),
) -> Response:
    """Return the document converted to the requested format."""
    import docreview360.api as _api_mod
    _api_mod._EXPORT_RATE_LIMITER.enforce(f"export:{current_user.username}:{_request_source(request)}")
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


# ---------------------------------------------------------------------------
# Archive routes
# ---------------------------------------------------------------------------

@router.post("/archive/{doc_id}", status_code=201, response_model=ArchiveRecord)
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


@router.get("/archive", response_model=list[ArchiveRecord])
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


@router.get("/archive/{archive_id}", response_model=ArchiveRecord)
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


@router.get("/archive/{archive_id}/report/{fmt}")
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


# ---------------------------------------------------------------------------
# Sign routes
# ---------------------------------------------------------------------------

@router.post("/sign/{doc_id}")
async def sign_document(
    doc_id: str,
    request: Request,
    user: str = Form(...),
    workflow: str | None = Form(None),
    approval: str | None = Form(None),
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, str]:
    """Create a signature request for ``doc_id`` using the active provider."""
    import docreview360.api as _api_mod
    _api_mod._SIGNATURE_RATE_LIMITER.enforce(f"sign:{user}:{_request_source(request)}")
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


@router.post("/sign/{sig_id}/complete")
async def complete_sign(
    sig_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> None:
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
    except (KeyError, ValueError) as exc:
        _logger.warning("handle_signature_return failed for sig_id %r: %s", sig_id, exc)


@router.get("/sign/{sig_id}")
async def get_sign_status(
    sig_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, str]:
    """Return signature status."""
    status = signature_status(sig_id)
    return {"status": status}


# ---------------------------------------------------------------------------
# Document Version Lineage endpoints
# ---------------------------------------------------------------------------


@router.get("/documents/{doc_id}/versions")
async def get_document_version_history(
    doc_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> list[dict[str, object]]:
    """Return the version history timeline for a document.

    Each entry contains ``revision_id``, ``version_number``, ``timestamp``,
    ``author``, and ``content_length`` (byte count) without transferring
    full content for every revision.
    """
    try:
        return get_version_history(doc_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/documents/{doc_id}/restore/{revision_id}", response_model=DocumentModel)
async def restore_version(
    doc_id: str,
    revision_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> DocumentModel:
    """Restore a document to a prior revision.

    The current content is saved as a new revision before the restore so the
    operation is reversible.  Returns HTTP 404 if the document or revision is
    not found, and HTTP 409 if the document is frozen.
    """
    try:
        return restore_document_version(doc_id, revision_id, author=current_user.username)
    except FrozenDocumentError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/documents/{doc_id}/freeze", response_model=DocumentModel)
async def freeze_doc(
    doc_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> DocumentModel:
    """Freeze a document at its current version.

    Once frozen, any attempt to update content returns HTTP 409.  Typically
    called automatically at approval stage to lock the reviewed version.
    """
    try:
        return freeze_document(doc_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/documents/{doc_id}/freeze", response_model=DocumentModel)
async def unfreeze_doc(
    doc_id: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> DocumentModel:
    """Lift the freeze on a document, allowing content changes again."""
    try:
        return unfreeze_document(doc_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/documents/{doc_id}/diff/{revision_id_a}/{revision_id_b}")
async def diff_revisions_endpoint(
    doc_id: str,
    revision_id_a: str,
    revision_id_b: str,
    current_user: auth.User = Depends(auth.get_current_user),
) -> dict[str, object]:
    """Return a redline (unified diff) between two document revisions.

    Use the special sentinel ``current`` as either revision ID to compare
    against the live document content.  The response includes:

    - ``unified_diff``: list of unified-diff lines
    - ``lines_added`` / ``lines_removed``: change counts
    - ``similarity_ratio``: 0–1 text similarity score
    - ``revision_a`` / ``revision_b``: revision metadata (id, version_number,
      timestamp, author)

    Returns 404 if the document or either revision is not found.
    """
    try:
        return diff_document_revisions(doc_id, revision_id_a, revision_id_b)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
