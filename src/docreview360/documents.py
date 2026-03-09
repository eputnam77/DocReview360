"""In-memory document storage and import helpers."""

from __future__ import annotations

import hashlib
import logging
import mimetypes
import re
import threading
from base64 import b64encode
from datetime import datetime, timezone
from difflib import SequenceMatcher
from io import BytesIO
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional
from uuid import uuid4

try:  # Optional dependency for HTML sanitization.
    import bleach
except ModuleNotFoundError:  # pragma: no cover - minimal installs
    bleach = None  # type: ignore[assignment]
from pydantic import BaseModel, Field, field_serializer

from . import fts
from .audit import log_audit_event
from .logs import log_event
from .settings_manager import load_settings

_logger = logging.getLogger(__name__)

DEFAULT_ALLOWED_MIME_TYPES: frozenset[str] = frozenset(
    {
        "text/plain",
        "text/markdown",
        "text/html",
        "application/json",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
)
DEFAULT_MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MiB

# Bleach's defaults omit headings which are common in Markdown content.  Extend the
# whitelist so Markdown-style HTML headings survive sanitisation while still
# removing unsafe elements such as ``<script>``.
if bleach is not None:
    _SANITIZE_TAGS: frozenset[str] = frozenset(
        set(bleach.sanitizer.ALLOWED_TAGS)
        | {"h1", "h2", "h3", "h4", "h5", "h6", "pre", "code"}
    )
else:  # pragma: no cover - fallback when bleach is missing
    _SANITIZE_TAGS = frozenset()

_SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)


IngestionPipeline = Callable[[bytes, str], str]


class IngestionRegistry:
    """Thread-safe registry mapping MIME types to ingestion pipelines."""

    def __init__(self) -> None:
        self._pipelines: dict[str, IngestionPipeline] = {}
        self._lock = threading.Lock()

    def register(self, mime_type: str, pipeline: IngestionPipeline) -> None:
        with self._lock:
            self._pipelines[mime_type.lower()] = pipeline

    def unregister(self, mime_type: str) -> None:
        with self._lock:
            self._pipelines.pop(mime_type.lower(), None)

    def get(self, mime_type: str) -> IngestionPipeline | None:
        with self._lock:
            return self._pipelines.get(mime_type.lower())

    def items(self) -> dict[str, IngestionPipeline]:
        with self._lock:
            return dict(self._pipelines)


ingestion_registry = IngestionRegistry()


def register_ingestion_pipeline(mime_type: str, pipeline: IngestionPipeline) -> None:
    """Register ``pipeline`` for ``mime_type``."""

    ingestion_registry.register(mime_type, pipeline)


def unregister_ingestion_pipeline(mime_type: str) -> None:
    """Remove any registered pipeline for ``mime_type``."""

    ingestion_registry.unregister(mime_type)


def get_ingestion_pipeline(mime_type: str) -> IngestionPipeline | None:
    """Return the pipeline registered for ``mime_type`` if any."""

    return ingestion_registry.get(mime_type)


_DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_PDF_MIME_TYPE = "application/pdf"


def _load_document_policy() -> tuple[int, frozenset[str], Mapping[str, Any]]:
    """Return upload policy from settings or sensible defaults."""

    settings = load_settings()
    doc_settings = settings.get("documents", {}) if isinstance(settings, dict) else {}
    max_size = doc_settings.get("max_upload_size", DEFAULT_MAX_UPLOAD_SIZE)
    try:
        size_limit = int(max_size)
    except (TypeError, ValueError):
        size_limit = DEFAULT_MAX_UPLOAD_SIZE
    if size_limit <= 0:
        size_limit = DEFAULT_MAX_UPLOAD_SIZE

    allowed = doc_settings.get("allowed_mime_types", DEFAULT_ALLOWED_MIME_TYPES)
    if isinstance(allowed, Iterable) and not isinstance(allowed, (str, bytes)):
        normalised: list[str] = []
        for item in allowed:
            if item is None:
                continue
            text = str(item).strip()
            if not text:
                continue
            normalised.append(text.lower())
        allowed_set = frozenset(normalised)
    else:
        allowed_set = DEFAULT_ALLOWED_MIME_TYPES

    if not allowed_set:
        allowed_set = DEFAULT_ALLOWED_MIME_TYPES

    return size_limit, allowed_set, doc_settings


def sanitize_content(content: str) -> str:
    """Scrub HTML/Markdown content using Bleach."""

    stripped = _SCRIPT_RE.sub("", content)
    if bleach is None:
        return stripped
    return bleach.clean(
        stripped,
        tags=_SANITIZE_TAGS,
        attributes=bleach.sanitizer.ALLOWED_ATTRIBUTES,
        protocols=bleach.sanitizer.ALLOWED_PROTOCOLS,
        strip=True,
    )


def _detect_mime_type(data: bytes, filename: str) -> str:
    """Best-effort MIME detection using ``python-magic`` with fallbacks."""

    mime: str | None = None
    try:  # pragma: no cover - dependency errors fall back to mimetypes
        import magic  # type: ignore[import-not-found]

    except Exception:  # pragma: no cover - optional dependency
        magic = None  # type: ignore[assignment]

    if magic is not None:
        try:
            detector = magic.Magic(mime=True)
            mime = detector.from_buffer(data)
        except Exception:  # pragma: no cover - libmagic failure
            mime = None

    if mime:
        mime = mime.split(";", 1)[0].strip().lower()
    else:
        mime, _ = mimetypes.guess_type(filename)
        if mime:
            mime = mime.lower()

    mime = mime or "application/octet-stream"
    if mime == "application/octet-stream":
        # Windows mimetypes can miss modern Office extensions; fall back to
        # filename-based detection for docx to avoid rejecting valid uploads.
        if filename.lower().endswith(".docx"):
            return _DOCX_MIME_TYPE
        try:
            decoded = data.decode("utf-8")
        except UnicodeDecodeError:
            return mime
        if all(char.isprintable() or char.isspace() for char in decoded):
            return "text/plain"

    return mime


class DocumentRevision(BaseModel):
    """Single revision of a document."""

    id: str
    timestamp: datetime
    content: str
    steps: list[Any] | None = None
    author: str = ""
    yjs_updates: list[bytes] | None = None

    @field_serializer("yjs_updates", when_used="json")
    def _ser_updates(self, updates: list[bytes] | None) -> list[str] | None:
        """Return base64 strings for binary Yjs updates.

        ``pydantic`` attempts to decode ``bytes`` as UTF-8 when serialising to
        JSON which fails for arbitrary binary data.  The dashboard API
        serialises full document models including revision history; any binary
        ``yjs_updates`` therefore triggered ``UnicodeDecodeError`` during
        ``model_dump``.  Encoding the updates as base64 preserves the data while
        keeping the output JSON serialisable.
        """

        if updates is None:
            return None
        return [b64encode(u).decode("ascii") for u in updates]


class DocumentModel(BaseModel):
    """Simple representation of a document with revision history."""

    id: str
    content: str
    history: List[DocumentRevision] = Field(default_factory=list)
    editor: str = "tiptap"
    number: int | None = None
    project: Optional[str] = None
    user: Optional[str] = None
    date: Optional[datetime] = None
    priority: Optional[int] = None
    ingestion_hash: str | None = None  # SHA-256 of original upload
    # Flag to mark public copies and track originating document
    public_copy: bool = False
    source_document_id: str | None = None
    # ``approval_ids`` previously used a mutable list as the default value.
    # In ``pydantic`` models this list is shared between instances which meant
    # adding an approval to one document unexpectedly appeared on others.
    # Using ``default_factory`` gives each model its own list.
    approval_ids: List[str] = Field(default_factory=list)


# Stored documents keyed by id
documents: Dict[str, DocumentModel] = {}
# Document ids that require a new review cycle
_re_review: set[str] = set()
# Track document numbers globally and per project
_next_document_number = 1
_project_document_numbers: Dict[str, int] = {}

# Guard shared document state in multithreaded scenarios
document_lock = threading.Lock()


def next_document_number(project: Optional[str] = None) -> int:
    """Return the next sequential document number for the project."""
    with document_lock:
        if project:
            current = _project_document_numbers.get(project, 0) + 1
            _project_document_numbers[project] = current
            return current
        global _next_document_number
        num = _next_document_number
        _next_document_number += 1
        return num


def _extract_docx_text(data: bytes) -> str:
    """Extract text from a DOCX file using ``python-docx``.

    Headings become Markdown ``#`` prefixes and tracked changes are represented
    with ``[INS:...]`` and ``[DEL:...]`` markers.
    """
    from docx import Document

    doc = Document(BytesIO(data))
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    parts: list[str] = []

    for para in doc.paragraphs:
        style = para.style.name if para.style is not None else ""
        prefix = ""
        if style.startswith("Heading"):
            try:
                level = int(style.split()[1])
            except (IndexError, ValueError):
                level = 1
            prefix = "#" * level + " "

        text_piece = ""
        for child in para._element.iterchildren():
            if child.tag == f"{ns}r":
                text_piece += "".join(t.text or "" for t in child.iter(f"{ns}t"))
            elif child.tag == f"{ns}ins":
                ins_text = "".join(t.text or "" for t in child.iter(f"{ns}t"))
                text_piece += f"[INS:{ins_text}]"
            elif child.tag == f"{ns}del":
                del_text = "".join(t.text or "" for t in child.iter(f"{ns}t"))
                text_piece += f"[DEL:{del_text}]"
        parts.append(prefix + text_piece)

    # Join paragraphs using real newline characters.  The previous
    # implementation mistakenly used the string ``"\\n"`` which produced a
    # literal backslash followed by ``n`` in the output instead of an actual
    # line break, yielding unreadable text when importing DOCX files.
    return "\n".join(parts)


def _default_docx_ingestion(data: bytes, filename: str) -> str:
    return _extract_docx_text(data)


register_ingestion_pipeline(_DOCX_MIME_TYPE, _default_docx_ingestion)


def _extract_pdf_text(data: bytes) -> str:
    """Extract textual content from a PDF using optional dependencies."""

    try:
        from pdfminer.high_level import extract_text  # type: ignore[import-not-found]
    except Exception:  # pragma: no cover - optional dependency
        extract_text = None  # type: ignore[assignment]

    if extract_text is not None:
        try:
            return extract_text(BytesIO(data)) or ""
        except Exception as exc:  # pragma: no cover - pdfminer failure
            _logger.debug("pdfminer extraction failed: %s", exc)

    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except Exception:  # pragma: no cover - optional dependency
        PdfReader = None  # type: ignore[assignment]

    if PdfReader is not None:
        try:
            reader = PdfReader(BytesIO(data))
            return "\n".join(filter(None, (page.extract_text() or "" for page in reader.pages)))
        except Exception as exc:  # pragma: no cover - pypdf failure
            _logger.debug("pypdf extraction failed: %s", exc)

    raise ValueError("PDF ingestion requires pdfminer.six or pypdf")


def _default_pdf_ingestion(data: bytes, filename: str) -> str:
    return _extract_pdf_text(data)


def _ensure_default_pipelines(doc_settings: Mapping[str, Any]) -> None:
    """Register or remove built-in pipelines based on configuration."""

    if doc_settings.get("enable_pdf_ingestion"):
        if get_ingestion_pipeline(_PDF_MIME_TYPE) is None:
            register_ingestion_pipeline(_PDF_MIME_TYPE, _default_pdf_ingestion)
    else:
        pipeline = get_ingestion_pipeline(_PDF_MIME_TYPE)
        if pipeline is _default_pdf_ingestion:
            unregister_ingestion_pipeline(_PDF_MIME_TYPE)


def _decode_text_payload(data: bytes) -> str:
    try:
        return data.decode()
    except UnicodeDecodeError as exc:
        raise ValueError("document bytes must be valid UTF-8") from exc


def import_document(
    filename: str,
    data: bytes,
    *,
    project: Optional[str] = None,
    user: Optional[str] = None,
    priority: Optional[int] = None,
) -> DocumentModel:
    """Create a document from uploaded bytes."""
    size_limit, allowed_types, doc_settings = _load_document_policy()
    if len(data) > size_limit:
        raise ValueError("document exceeds configured size limit")

    mime_type = _detect_mime_type(data, filename)
    if mime_type not in allowed_types:
        raise ValueError(f"unsupported MIME type: {mime_type}")

    _ensure_default_pipelines(doc_settings)

    pipeline = get_ingestion_pipeline(mime_type)
    if pipeline is None and filename.lower().endswith(".docx"):
        pipeline = _default_docx_ingestion

    if mime_type == _PDF_MIME_TYPE:
        if pipeline is None:
            raise ValueError(
                "no PDF ingestion pipeline available; enable documents.enable_pdf_ingestion "
                "or register a custom pipeline"
            )
        if pipeline is _default_pdf_ingestion and not doc_settings.get(
            "enable_pdf_ingestion", False
        ):
            raise ValueError(
                "PDF ingestion is disabled; set documents.enable_pdf_ingestion to true"
            )

    if pipeline is not None:
        content = pipeline(data, filename)
    else:
        content = _decode_text_payload(data)

    content = sanitize_content(content)

    doc_id = uuid4().hex
    ingestion_hash = hashlib.sha256(data).hexdigest()
    revision = DocumentRevision(
        id=uuid4().hex,
        timestamp=datetime.now(timezone.utc),
        content=content,
        steps=None,
        author=user or "",
    )
    document = DocumentModel(
        id=doc_id,
        content=content,
        history=[revision],
        number=next_document_number(project),
        project=project,
        user=user,
        date=datetime.now(timezone.utc),
        priority=priority,
        ingestion_hash=ingestion_hash,
    )
    with document_lock:
        documents[doc_id] = document
    # Index the document for search without creating an import cycle
    from . import search as search_module

    search_module.add_document(document)
    if content.strip():
        fts.index_document(doc_id, content)
    log_audit_event(
        doc_id,
        "created",
        actor=user,
        project=project,
        filename=filename,
    )
    return document


def get_document(doc_id: str) -> DocumentModel | None:
    """Return a document by id."""
    return documents.get(doc_id)


def list_documents() -> list[DocumentModel]:
    """Return all documents."""
    return list(documents.values())


def list_public_documents() -> list[DocumentModel]:
    """Return documents marked as public copies."""
    return [d for d in documents.values() if d.public_copy]


def public_documents_report() -> list[dict[str, str | None]]:
    """Return minimal metadata for public documents.

    Each entry contains the public document id and the originating
    ``source_document_id`` so external systems can trace back to the
    internal record.
    """
    return [
        {"id": d.id, "source_document_id": d.source_document_id}
        for d in documents.values()
        if d.public_copy
    ]


def link_approval(doc_id: str, approval_id: str) -> None:
    """Associate ``approval_id`` with ``doc_id`` and log the action."""
    document = documents.get(doc_id)
    if document is None:
        raise KeyError("document not found")
    if approval_id not in document.approval_ids:
        document.approval_ids.append(approval_id)
        log_event(
            "approval_linked",
            doc_id=doc_id,
            approval_id=approval_id,
        )
        log_audit_event(doc_id, "approval_linked", approval_id=approval_id)


def unlink_approval(doc_id: str, approval_id: str) -> None:
    """Remove ``approval_id`` from ``doc_id`` and log the action."""
    document = documents.get(doc_id)
    if document is None:
        return
    if approval_id in document.approval_ids:
        document.approval_ids.remove(approval_id)
        log_event(
            "approval_unlinked",
            doc_id=doc_id,
            approval_id=approval_id,
        )
        log_audit_event(doc_id, "approval_unlinked", approval_id=approval_id)


def update_document(
    doc_id: str,
    content: str,
    *,
    priority: Optional[int] = None,
    steps: list[Any] | None = None,
    author: str | None = None,
    yjs_updates: list[bytes] | None = None,
) -> tuple[DocumentModel, str]:
    """Replace document content and record a new revision."""
    document = documents.get(doc_id)
    if document is None:
        raise KeyError(f"Document '{doc_id}' not found")
    content = sanitize_content(content)
    # Remove the old version from the search index before updating
    from . import search as search_module

    search_module.search_index.remove_document(doc_id)
    fts.remove_document(doc_id)

    with document_lock:
        old_content = document.content
        revision_id = uuid4().hex
        document.content = content
        document.history.append(
            DocumentRevision(
                id=revision_id,
                timestamp=datetime.now(timezone.utc),
                content=content,
                steps=steps,
                author=author or document.user or "",
                yjs_updates=yjs_updates,
            )
        )
        if priority is not None:
            document.priority = priority
        if author is not None:
            document.user = author

    matcher = SequenceMatcher(None, old_content, content)
    quick_bound = matcher.real_quick_ratio()
    if quick_bound >= 0.7 and matcher.ratio() < 0.7:
        with document_lock:
            _re_review.add(doc_id)
    elif quick_bound < 0.7:
        with document_lock:
            _re_review.add(doc_id)

    # Re-index the updated document
    search_module.add_document(document)
    if document.content.strip():
        fts.index_document(doc_id, document.content)
    log_audit_event(doc_id, "updated", actor=author or document.user, priority=priority)

    return document, revision_id


def autosave_document(doc_id: str, content: str) -> tuple[DocumentModel, str]:
    """Save content if it changed, preserving history."""
    document = documents.get(doc_id)
    if document is None:
        raise KeyError(f"Document '{doc_id}' not found")
    if not document.history:
        revision_id = uuid4().hex
        with document_lock:
            document.history.append(
                DocumentRevision(
                    id=revision_id,
                    timestamp=datetime.now(timezone.utc),
                    content=document.content,
                    steps=None,
                    author=document.user or "",
                )
            )
        if document.content.strip():
            from . import search as search_module

            search_module.add_document(document)
            fts.index_document(doc_id, document.content)
        return document, revision_id
    if document.content == content:
        return document, document.history[-1].id
    return update_document(doc_id, content)


def needs_rereview(doc_id: str) -> bool:
    """Return ``True`` if the document was changed substantially."""
    return doc_id in _re_review


def clear_rereview(doc_id: str) -> None:
    """Remove the re-review flag for ``doc_id``."""
    with document_lock:
        _re_review.discard(doc_id)


def get_document_versions(doc_id: str) -> list[str]:
    """Return the list of all versions for ``doc_id``."""
    document = documents.get(doc_id)
    if document is None:
        raise KeyError(f"Document '{doc_id}' not found")
    return [rev.content for rev in document.history]


def get_document_version(doc_id: str, index: int) -> str:
    """Return a specific version for ``doc_id``."""
    versions = get_document_versions(doc_id)
    if index < 0 or index >= len(versions):
        raise IndexError("version index out of range")
    return versions[index]


def set_document_editor(doc_id: str, editor: str) -> DocumentModel:
    """Set the preferred editor for ``doc_id`` and return the document."""
    if not isinstance(editor, str):
        raise TypeError("editor must be a string")
    editor_name = editor.strip()
    if not editor_name:
        raise ValueError("editor required")
    document = documents.get(doc_id)
    if document is None:
        raise KeyError(f"document '{doc_id}' not found")
    document.editor = editor_name
    return document


def get_document_editor(doc_id: str) -> str:
    """Return the preferred editor for ``doc_id``."""
    document = documents.get(doc_id)
    if document is None:
        raise KeyError(f"document '{doc_id}' not found")
    return document.editor
