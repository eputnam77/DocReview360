# SPDX-License-Identifier: MIT
"""Document type registry — CRUD, import/export, default data, DB-backed view."""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Iterator, MutableMapping
from typing import Any, Dict, List

from pydantic import ValidationError
from sqlalchemy import delete, select

from ..db_store import get_db
from ..models import DocumentType as DocumentTypeORM
from ._models import DocumentTypeModel, _validate_workflow

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default data
# ---------------------------------------------------------------------------

DEFAULT_DOC_TYPE_PHASES: Dict[str, List[str]] = {
    "Advisory Circular": [
        "Draft Development",
        "Internal Coordination",
        "Final Issuance",
    ],
    "Order / Directive": [
        "Draft Development",
        "Internal Coordination",
        "Final Issuance",
    ],
    "Policy": [
        "Draft Development",
        "Internal Coordination",
        "Final Issuance",
    ],
    "Guidance": [
        "Draft Development",
        "Internal Coordination",
        "Final Issuance",
    ],
    "Memorandum": [
        "Draft Development",
        "Internal Coordination",
        "Final Issuance",
    ],
    "SOP": [
        "Draft Development",
        "Peer Review",
        "Internal Coordination",
        "Final Issuance",
    ],
    "Desk Guide": [
        "Draft Development",
        "Peer Review",
        "Internal Coordination",
        "Final Issuance",
    ],
    "Manual / Handbook": [
        "Draft Development",
        "Peer Review",
        "Internal Coordination",
        "Final Issuance",
    ],
    "Report": [
        "Draft Development",
        "Peer Review",
        "Final Issuance",
    ],
    "Audit Report": [
        "Draft Development",
        "Peer Review",
        "Internal Coordination",
        "Final Issuance",
    ],
    "After-Action Report": [
        "Draft Development",
        "Peer Review",
        "Final Issuance",
    ],
    "Briefing / Slide Deck": [
        "Draft Development",
        "Internal Coordination",
        "Final Issuance",
    ],
    "Meeting Minutes": [
        "Draft Development",
        "Internal Coordination",
        "Final Issuance",
    ],
    "Federal Register Notice": [
        "Draft Development",
        "Internal Coordination",
        "Public Comment / Proposed Rulemaking",
        "Final Issuance",
    ],
    "Proposed Rule / NPRM": [
        "Draft Development",
        "Internal Coordination",
        "Public Comment / Proposed Rulemaking",
        "Final Issuance",
    ],
    "Final Rule": [
        "Draft Development",
        "Internal Coordination",
        "Public Comment / Proposed Rulemaking",
        "Final Issuance",
    ],
    "Supporting Statement (PRA)": [
        "Draft Development",
        "Internal Coordination",
        "Public Comment / Proposed Rulemaking",
        "Final Issuance",
    ],
    "ICR": [
        "Draft Development",
        "Internal Coordination",
        "Public Comment / Proposed Rulemaking",
        "Final Issuance",
    ],
    "Exemption / Waiver": [
        "Draft Development",
        "Internal Coordination",
        "Public Comment / Proposed Rulemaking",
        "Final Issuance",
    ],
    "Special Conditions": [
        "Draft Development",
        "Internal Coordination",
        "Public Comment / Proposed Rulemaking",
        "Final Issuance",
    ],
    "FAQ": [
        "Draft Development",
        "Internal Review",
        "Publication",
    ],
    "Letter / Correspondence": [
        "Draft Development",
        "Internal Review",
        "Publication",
    ],
    "Web Content": [
        "Draft Development",
        "Internal Review",
        "Publication",
    ],
    "Release Notes": [
        "Draft Development",
        "Peer Review",
        "Release Candidate Review",
        "General Availability",
        "Maintenance / Revision Cycle",
    ],
    "User Guide": [
        "Draft Development",
        "Peer Review",
        "Release Candidate Review",
        "General Availability",
        "Maintenance / Revision Cycle",
    ],
    "API Manual / API Reference": [
        "Draft Development",
        "Peer Review",
        "Release Candidate Review",
        "General Availability",
        "Maintenance / Revision Cycle",
    ],
    "README": [
        "Draft Development",
        "Peer Review",
        "Release Candidate Review",
        "General Availability",
        "Maintenance / Revision Cycle",
    ],
}

DEFAULT_DOC_TYPE_NAMES = list(DEFAULT_DOC_TYPE_PHASES.keys())

# ---------------------------------------------------------------------------
# Curated starter HTML templates per document type
# ---------------------------------------------------------------------------

DEFAULT_DOC_TYPE_TEMPLATES: Dict[str, str] = {
    "Advisory Circular": (
        "<h1>Advisory Circular [AC Number]: [Title]</h1>"
        "<h2>1. Purpose</h2>"
        "<p>This advisory circular (AC) provides guidance on [topic]. "
        "It is issued under [authority].</p>"
        "<h2>2. Applicability</h2>"
        "<p>This AC applies to [scope / affected parties].</p>"
        "<h2>3. Background</h2>"
        "<p>[Provide context and background for why this guidance is needed.]</p>"
        "<h2>4. Guidance</h2>"
        "<h3>4.1 [Subtopic]</h3>"
        "<p>[Guidance text.]</p>"
        "<h2>5. Related Documents</h2>"
        "<p>[List related regulations, orders, or guidance documents.]</p>"
        "<h2>6. Contact</h2>"
        "<p>Questions about this AC should be directed to [office / contact information].</p>"
    ),
    "Memorandum": (
        "<h1>MEMORANDUM</h1>"
        "<p><strong>DATE:</strong> [Date]</p>"
        "<p><strong>TO:</strong> [Recipients]</p>"
        "<p><strong>FROM:</strong> [Author / Office]</p>"
        "<p><strong>SUBJECT:</strong> [Subject]</p>"
        "<h2>Purpose</h2>"
        "<p>[State the purpose of this memorandum.]</p>"
        "<h2>Background</h2>"
        "<p>[Provide relevant background information.]</p>"
        "<h2>Discussion</h2>"
        "<p>[Present the main points and analysis.]</p>"
        "<h2>Action Required</h2>"
        "<p>[Describe any actions required and deadlines.]</p>"
        "<h2>Point of Contact</h2>"
        "<p>[Contact information for questions.]</p>"
    ),
    "Policy": (
        "<h1>[Policy Title]</h1>"
        "<p><strong>Policy Number:</strong> [Number]</p>"
        "<p><strong>Effective Date:</strong> [Date]</p>"
        "<p><strong>Review Date:</strong> [Date]</p>"
        "<h2>1. Purpose</h2>"
        "<p>[State the purpose and intent of this policy.]</p>"
        "<h2>2. Scope</h2>"
        "<p>[Define who this policy applies to.]</p>"
        "<h2>3. Policy Statement</h2>"
        "<p>[State the policy clearly and concisely.]</p>"
        "<h2>4. Responsibilities</h2>"
        "<ul><li><strong>[Role]:</strong> [Responsibilities]</li></ul>"
        "<h2>5. Procedures</h2>"
        "<p>[Describe procedures for implementing the policy.]</p>"
        "<h2>6. Enforcement</h2>"
        "<p>[Describe consequences for non-compliance.]</p>"
        "<h2>7. Related Documents</h2>"
        "<p>[List related policies, regulations, or standards.]</p>"
    ),
    "Order / Directive": (
        "<h1>[Order / Directive Title]</h1>"
        "<p><strong>Order Number:</strong> [Number]</p>"
        "<p><strong>Effective Date:</strong> [Date]</p>"
        "<p><strong>Issuing Authority:</strong> [Office]</p>"
        "<h2>1. Purpose</h2>"
        "<p>[State the purpose of this order or directive.]</p>"
        "<h2>2. Authority</h2>"
        "<p>[Cite the legal or regulatory authority under which this order is issued.]</p>"
        "<h2>3. Applicability</h2>"
        "<p>[Define the scope of persons or entities covered.]</p>"
        "<h2>4. Requirements</h2>"
        "<ol><li>[Requirement 1]</li><li>[Requirement 2]</li></ol>"
        "<h2>5. Responsibilities</h2>"
        "<ul><li><strong>[Role]:</strong> [Responsibility]</li></ul>"
        "<h2>6. Cancellation</h2>"
        "<p>[Identify any orders or directives this supersedes.]</p>"
    ),
    "SOP": (
        "<h1>Standard Operating Procedure: [Title]</h1>"
        "<p><strong>SOP Number:</strong> [Number]</p>"
        "<p><strong>Version:</strong> [Version]</p>"
        "<p><strong>Effective Date:</strong> [Date]</p>"
        "<h2>1. Purpose</h2>"
        "<p>[Describe what this SOP accomplishes and why it is needed.]</p>"
        "<h2>2. Scope</h2>"
        "<p>[Define who performs this procedure and when.]</p>"
        "<h2>3. Responsibilities</h2>"
        "<ul><li><strong>[Role]:</strong> [Responsibility]</li></ul>"
        "<h2>4. Required Materials / Prerequisites</h2>"
        "<ul><li>[Material or prerequisite]</li></ul>"
        "<h2>5. Procedure</h2>"
        "<ol><li>[Step 1]</li><li>[Step 2]</li><li>[Step 3]</li></ol>"
        "<h2>6. Safety / Compliance Notes</h2>"
        "<p>[List any safety precautions or compliance requirements.]</p>"
        "<h2>7. References</h2>"
        "<p>[List related documents or standards.]</p>"
    ),
    "Report": (
        "<h1>[Report Title]</h1>"
        "<p><strong>Prepared by:</strong> [Author / Office]</p>"
        "<p><strong>Date:</strong> [Date]</p>"
        "<p><strong>Report Number:</strong> [Number]</p>"
        "<h2>Executive Summary</h2>"
        "<p>[Provide a brief overview of the key findings and recommendations.]</p>"
        "<h2>1. Introduction</h2>"
        "<p>[Describe the purpose, scope, and background of this report.]</p>"
        "<h2>2. Findings</h2>"
        "<h3>2.1 [Finding Category]</h3>"
        "<p>[Describe findings.]</p>"
        "<h2>3. Analysis</h2>"
        "<p>[Analyze the findings and their implications.]</p>"
        "<h2>4. Recommendations</h2>"
        "<ol><li><strong>Recommendation 1:</strong> [Description]</li></ol>"
        "<h2>5. Conclusion</h2>"
        "<p>[Summarize the report's conclusions.]</p>"
        "<h2>Appendices</h2>"
        "<p>[List any supporting materials.]</p>"
    ),
    "FAQ": (
        "<h1>Frequently Asked Questions: [Topic]</h1>"
        "<h2>General Questions</h2>"
        "<h3>Q: [Question]</h3>"
        "<p>A: [Answer]</p>"
        "<h3>Q: [Question]</h3>"
        "<p>A: [Answer]</p>"
        "<h2>Technical Questions</h2>"
        "<h3>Q: [Question]</h3>"
        "<p>A: [Answer]</p>"
        "<h2>Contact</h2>"
        "<p>If your question is not answered here, contact [office / email].</p>"
    ),
    "Release Notes": (
        "<h1>Release Notes — [Product Name] v[Version]</h1>"
        "<p><strong>Release Date:</strong> [Date]</p>"
        "<p><strong>Release Type:</strong> [Major / Minor / Patch]</p>"
        "<h2>What's New</h2>"
        "<ul><li>[New feature or enhancement]</li></ul>"
        "<h2>Bug Fixes</h2>"
        "<ul><li>[Bug fix description]</li></ul>"
        "<h2>Known Issues</h2>"
        "<ul><li>[Known issue and workaround if available]</li></ul>"
        "<h2>Upgrade Notes</h2>"
        "<p>[Describe any breaking changes or migration steps required.]</p>"
        "<h2>Compatibility</h2>"
        "<p>[List supported platforms, dependencies, or system requirements.]</p>"
    ),
    "User Guide": (
        "<h1>[Product Name] User Guide</h1>"
        "<p><strong>Version:</strong> [Version]</p>"
        "<p><strong>Last Updated:</strong> [Date]</p>"
        "<h2>Introduction</h2>"
        "<p>[Brief overview of the product and this guide's purpose.]</p>"
        "<h2>Getting Started</h2>"
        "<h3>Prerequisites</h3>"
        "<ul><li>[Prerequisite]</li></ul>"
        "<h3>Installation</h3>"
        "<ol><li>[Step 1]</li><li>[Step 2]</li></ol>"
        "<h2>Core Features</h2>"
        "<h3>[Feature Name]</h3>"
        "<p>[Description and instructions for the feature.]</p>"
        "<h2>Troubleshooting</h2>"
        "<h3>[Common Issue]</h3>"
        "<p>[Resolution steps.]</p>"
        "<h2>Support</h2>"
        "<p>Contact [support channel] for assistance.</p>"
    ),
    "Guidance": (
        "<h1>[Guidance Document Title]</h1>"
        "<p><strong>Document Number:</strong> [Number]</p>"
        "<p><strong>Date:</strong> [Date]</p>"
        "<h2>1. Purpose</h2>"
        "<p>[Describe the purpose and scope of this guidance.]</p>"
        "<h2>2. Background</h2>"
        "<p>[Provide context and regulatory background.]</p>"
        "<h2>3. Guidance</h2>"
        "<p>[Present the guidance clearly.]</p>"
        "<h2>4. Questions</h2>"
        "<p>[Contact information for questions about this guidance.]</p>"
    ),
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_explicit_clear_active: bool = False
_explicit_clear_lock = threading.Lock()
"""Guards reads and writes of ``_explicit_clear_active`` across threads."""


def _bootstrap_if_empty() -> None:
    """Seed default document types when the table is empty."""
    global _explicit_clear_active

    with _explicit_clear_lock:
        if _explicit_clear_active:
            return

    db = get_db()
    with db.session() as conn:
        from sqlalchemy import text as _text

        count = conn.execute(_text("SELECT COUNT(*) FROM document_types")).scalar()
        if count:
            return
        with _explicit_clear_lock:
            _explicit_clear_active = False
        for order, (name, phases) in enumerate(DEFAULT_DOC_TYPE_PHASES.items(), start=1):
            template = DEFAULT_DOC_TYPE_TEMPLATES.get(name, f"<h1>{name}</h1>")
            conn.execute(
                _text(
                    "INSERT OR IGNORE INTO document_types "
                    "(name, template, workflow, display_order) "
                    "VALUES (:name, :template, :workflow, :order)"
                ),
                {
                    "name": name,
                    "template": template,
                    "workflow": json.dumps(phases),
                    "order": order,
                },
            )


def _row_to_model(row: Any) -> DocumentTypeModel:
    """Convert a DB row (or ORM object) to :class:`DocumentTypeModel`."""
    if isinstance(row, DocumentTypeORM):
        workflow = row.workflow if isinstance(row.workflow, list) else json.loads(
            row.workflow or "[]"
        )
        return DocumentTypeModel(
            name=row.name,
            template=row.template or "",
            workflow=workflow,
            default_workflow_template_id=row.default_workflow_template_id,
        )
    name = row.name if hasattr(row, "name") else row[0]
    template = row.template if hasattr(row, "template") else (row[1] if len(row) > 1 else "")
    raw_workflow = (
        row.workflow if hasattr(row, "workflow") else (row[2] if len(row) > 2 else "[]")
    )
    workflow = raw_workflow if isinstance(raw_workflow, list) else json.loads(raw_workflow or "[]")
    # Raw SQL rows return the DB column name `default_template_id`; check both names for compat.
    default_workflow_template_id = (
        row.default_workflow_template_id
        if hasattr(row, "default_workflow_template_id")
        else (
            row.default_template_id
            if hasattr(row, "default_template_id")
            else (row[3] if len(row) > 3 else None)
        )
    )
    return DocumentTypeModel(
        name=name,
        template=template or "",
        workflow=workflow,
        default_workflow_template_id=default_workflow_template_id,
    )


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------


def add_document_type(doc_type: DocumentTypeModel | dict[str, Any]) -> DocumentTypeModel:
    """Store a document type in the database."""
    if isinstance(doc_type, dict):
        doc_type = DocumentTypeModel(**doc_type)
    else:
        doc_type = DocumentTypeModel.model_validate(doc_type.model_dump())
    _validate_workflow(doc_type)

    if not doc_type.name.strip():
        raise ValueError("Document type name must not be empty")

    from sqlalchemy import text as _text

    db = get_db()
    with db.session() as conn:
        existing = conn.execute(
            select(
                DocumentTypeORM.name,
                DocumentTypeORM.template,
                DocumentTypeORM.workflow,
                DocumentTypeORM.default_workflow_template_id,
            ).where(DocumentTypeORM.name == doc_type.name)
        ).one_or_none()

        if existing is not None:
            existing_model = _row_to_model(existing)
            if existing_model.model_dump() != doc_type.model_dump():
                raise ValueError(f"Document type '{doc_type.name}' already exists")
            return existing_model

        conn.execute(
            _text(
                "INSERT INTO document_types (name, template, workflow, default_template_id) "
                "VALUES (:name, :template, :workflow, :dtid)"
            ),
            {
                "name": doc_type.name,
                "template": doc_type.template,
                "workflow": json.dumps(doc_type.workflow),
                "dtid": doc_type.default_workflow_template_id,
            },
        )
    return doc_type


def get_document_type(name: str) -> DocumentTypeModel | None:
    """Retrieve a document type by name."""
    _bootstrap_if_empty()
    db = get_db()
    with db.session() as conn:
        row = conn.execute(
            select(
                DocumentTypeORM.name,
                DocumentTypeORM.template,
                DocumentTypeORM.workflow,
                DocumentTypeORM.default_workflow_template_id,
            ).where(DocumentTypeORM.name == name)
        ).one_or_none()
        if row is None:
            return None
        return _row_to_model(row)


def list_document_types() -> list[DocumentTypeModel]:
    """Return all known document types sorted alphabetically by name."""
    _bootstrap_if_empty()
    db = get_db()
    with db.session() as conn:
        rows = conn.execute(
            select(
                DocumentTypeORM.name,
                DocumentTypeORM.template,
                DocumentTypeORM.workflow,
                DocumentTypeORM.default_workflow_template_id,
            ).order_by(DocumentTypeORM.name)
        ).all()
        return [_row_to_model(row) for row in rows]


def update_document_type(name: str, doc_type: DocumentTypeModel) -> DocumentTypeModel:
    """Update an existing document type and persist changes."""
    existing = get_document_type(name)
    if existing is None:
        raise KeyError(f"Document type '{name}' not found")

    doc_type = DocumentTypeModel.model_validate(doc_type.model_dump())
    _validate_workflow(doc_type)

    from sqlalchemy import text as _text

    if doc_type.name != name:
        if get_document_type(doc_type.name) is not None:
            raise ValueError(f"Document type '{doc_type.name}' already exists")

        try:
            from ..search import projects

            for proj in projects.values():
                if proj.doc_type == name:
                    proj.doc_type = doc_type.name
        except Exception as exc:  # pragma: no cover - best-effort
            _logger.warning("Failed to update in-memory project doc_type on rename: %s", exc)

    db = get_db()
    with db.session() as conn:
        conn.execute(
            _text(
                "UPDATE document_types SET name=:new_name, template=:template, "
                "workflow=:workflow, default_template_id=:dtid WHERE name=:old_name"
            ),
            {
                "old_name": name,
                "new_name": doc_type.name,
                "template": doc_type.template,
                "workflow": json.dumps(doc_type.workflow),
                "dtid": doc_type.default_workflow_template_id,
            },
        )
    return doc_type


def delete_document_type(name: str) -> None:
    """Delete a document type by name."""
    db = get_db()
    with db.session() as conn:
        result = conn.execute(
            delete(DocumentTypeORM).where(DocumentTypeORM.name == name)
        )
        if result.rowcount == 0:
            raise KeyError(f"Document type '{name}' not found")


# ---------------------------------------------------------------------------
# Import / Export
# ---------------------------------------------------------------------------


def export_document_types(path: str) -> None:
    """Serialize document types to *path* as JSON."""
    from pathlib import Path

    try:
        dest = Path(path)
        if dest.is_dir():
            raise ValueError(f"Export path {dest} must be a file")
        dest.parent.mkdir(parents=True, exist_ok=True)
        json_data = [doc.model_dump() for doc in list_document_types()]
        dest.write_text(json.dumps(json_data, indent=2))
    except OSError as exc:
        raise RuntimeError(f"Failed to export document types to {path}") from exc


def import_document_types(path: str) -> None:
    """Load document types from a JSON file and persist to DB."""
    from pathlib import Path

    try:
        data = json.loads(Path(path).read_text())
    except OSError as exc:
        raise RuntimeError(f"Failed to read document types from {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}") from exc

    if not isinstance(data, list):
        raise ValueError("JSON must contain a list of document types")

    temp: dict[str, DocumentTypeModel] = {}
    for item in data:
        try:
            doc = DocumentTypeModel(**item)
            _validate_workflow(doc)
        except ValidationError as exc:
            raise ValueError(f"Invalid document type entry: {item}") from exc
        temp[doc.name] = doc

    db = get_db()
    with db.session() as conn:
        from sqlalchemy import text as _text

        conn.execute(_text("DELETE FROM document_types"))
        for doc in temp.values():
            conn.execute(
                _text(
                    "INSERT INTO document_types (name, template, workflow, default_template_id) "
                    "VALUES (:name, :template, :workflow, :dtid)"
                ),
                {
                    "name": doc.name,
                    "template": doc.template,
                    "workflow": json.dumps(doc.workflow),
                    "dtid": doc.default_workflow_template_id,
                },
            )


def export_document_types_json() -> str:
    """Return document types as a JSON string."""
    json_data = [doc.model_dump() for doc in list_document_types()]
    return json.dumps(json_data, indent=2)


def import_document_types_json(data: str) -> None:
    """Load document types from a JSON string and persist to DB."""
    try:
        payload = json.loads(data)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON payload") from exc

    if not isinstance(payload, list):
        raise ValueError("JSON must contain a list of document types")

    temp: dict[str, DocumentTypeModel] = {}
    for item in payload:
        try:
            doc = DocumentTypeModel(**item)
            _validate_workflow(doc)
        except ValidationError as exc:
            raise ValueError(f"Invalid document type entry: {item}") from exc
        temp[doc.name] = doc

    db = get_db()
    with db.session() as conn:
        from sqlalchemy import text as _text

        conn.execute(_text("DELETE FROM document_types"))
        for doc in temp.values():
            conn.execute(
                _text(
                    "INSERT INTO document_types (name, template, workflow, default_template_id) "
                    "VALUES (:name, :template, :workflow, :dtid)"
                ),
                {
                    "name": doc.name,
                    "template": doc.template,
                    "workflow": json.dumps(doc.workflow),
                    "dtid": doc.default_workflow_template_id,
                },
            )


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def list_all_phases() -> list[str]:
    """Return a sorted list of all unique phases across all document types."""
    phases: set[str] = set()
    for doc in list_document_types():
        for phase in doc.workflow:
            phases.add(phase)
    return sorted(phases)


def reset_document_types(seed: bool = True) -> None:
    """Clear all document types and optionally re-seed defaults."""
    global _explicit_clear_active

    from sqlalchemy import text as _text

    db = get_db()
    with db.session() as conn:
        conn.execute(_text("DELETE FROM document_types"))
        with _explicit_clear_lock:
            if seed:
                _explicit_clear_active = False
                for order, (name, phases) in enumerate(DEFAULT_DOC_TYPE_PHASES.items(), start=1):
                    template = DEFAULT_DOC_TYPE_TEMPLATES.get(name, f"<h1>{name}</h1>")
                    conn.execute(
                        _text(
                            "INSERT INTO document_types "
                            "(name, template, workflow, display_order) "
                            "VALUES (:name, :template, :workflow, :order)"
                        ),
                        {
                            "name": name,
                            "template": template,
                            "workflow": json.dumps(phases),
                            "order": order,
                        },
                    )
            else:
                _explicit_clear_active = True


# ---------------------------------------------------------------------------
# Backward-compatible dict-like view
# ---------------------------------------------------------------------------


class _DocumentTypesView(MutableMapping):
    """A dict-like view over the database-backed document types."""

    def __getitem__(self, key: str) -> DocumentTypeModel:
        result = get_document_type(key)
        if result is None:
            raise KeyError(key)
        return result

    def __setitem__(self, key: str, value: DocumentTypeModel) -> None:
        if get_document_type(key) is not None:
            update_document_type(key, value)
        else:
            add_document_type(value)

    def __delitem__(self, key: str) -> None:
        delete_document_type(key)

    def __iter__(self) -> Iterator[str]:
        return iter(dt.name for dt in list_document_types())

    def __len__(self) -> int:
        from sqlalchemy import text as _text

        db = get_db()
        with db.session() as conn:
            result = conn.execute(
                _text("SELECT COUNT(*) FROM document_types")
            ).scalar()
            return int(result or 0)

    def clear(self) -> None:  # type: ignore[override]
        """Remove all document types from the database (without re-seeding)."""
        reset_document_types(seed=False)


# Module-level dict-like object backed by the database.
document_types: MutableMapping[str, DocumentTypeModel] = _DocumentTypesView()

# ---------------------------------------------------------------------------
# Backward-compat stubs for old file-based symbols
# ---------------------------------------------------------------------------

DATA_FILE: Any = None


def save_state() -> None:  # pragma: no cover
    """No-op kept for backward compatibility with tests."""
