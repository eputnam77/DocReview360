# SPDX-License-Identifier: MIT
"""General AI chatbot for DocReview360 content and document writing questions."""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

_logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .search import ProjectModel
else:
    ProjectModel = Any
projects: dict[str, Any]
try:
    from .search import list_projects, overdue_high_priority
    from .search import projects as _projects

    projects = _projects
except Exception:

    def list_projects(user: str | None = None) -> list[ProjectModel]:
        return []

    def overdue_high_priority() -> list[str]:
        return []

    projects = {}


try:
    from .workflows import workflows
except Exception:
    workflows = {}

try:
    from .approvals import approvals
except Exception:
    approvals = {}

try:
    from .doc_types import document_types
except Exception:
    document_types = {}

# Define templates data structure based on frontend templates
TEMPLATES = [
    {
        "id": "faa_ac",
        "label": "FAA Advisory Circular (TipTap)",
        "type": "tiptap",
    },
    {
        "id": "business_letter",
        "label": "Business Letter Template",
        "type": "word",
    },
    {
        "id": "memo_template",
        "label": "Memo Template",
        "type": "word",
    },
    {
        "id": "report_template",
        "label": "Report Template",
        "type": "word",
    },
    {
        "id": "proposal_template",
        "label": "Proposal Template",
        "type": "word",
    },
    {
        "id": "meeting_minutes",
        "label": "Meeting Minutes Template",
        "type": "word",
    },
]


def _assignment_question(lower: str) -> str | None:
    who = re.search(r"who is assigned to (?:project )?([\w-]+)", lower)
    if not who:
        return None
    proj_id = who.group(1)
    proj = projects.get(proj_id)
    if proj is None:
        return f"Project {proj_id} not found."
    user = proj.temp_user or proj.user
    return f"{user} is assigned to {proj_id}." if user else f"No user assigned to {proj_id}."


def _status_question(lower: str) -> str | None:
    status = re.search(r"(?:what is the )?status of (?:project )?([\w-]+)", lower)
    if not status:
        return None
    proj_id = status.group(1)
    proj = projects.get(proj_id)
    if proj is None:
        return f"Project {proj_id} not found."
    if proj.workflow:
        wf = workflows.get(proj.workflow)
        if wf:
            return f"{proj_id} is currently in the {wf.phase.lower()} phase."
    return f"{proj_id} is currently in the {proj.status.lower()} phase."


def _workload_question(lower: str) -> str | None:
    workload = re.search(
        r"what is (?:the )?workload (?:for )?(?:user )?([\w-]+)",
        lower,
    ) or re.search(
        r"how many (?:projects|items) (?:are )?(?:assigned to )?(?:user )?([\w-]+)",
        lower,
    )
    if not workload:
        return None
    user = workload.group(1)
    user_projects = list_projects(user)
    count = len(user_projects)
    if count == 0:
        return f"{user} has no projects assigned."
    if count == 1:
        return f"{user} has 1 project assigned."
    return f"{user} has {count} projects assigned."


def _overdue_question(lower: str) -> str | None:
    if "overdue" not in lower or ("project" not in lower and "high priority" not in lower):
        return None
    overdue = overdue_high_priority()
    count = len(overdue)
    if count == 0:
        return "There are no overdue high priority projects."
    if count == 1:
        return "There is 1 overdue high priority project."
    return f"There are {count} overdue high priority projects."


def _current_document_types() -> dict[str, Any]:
    """Return the active document type registry."""

    try:
        from .doc_types import document_types as doc_types_map

        return doc_types_map
    except Exception:
        return document_types


def _template_question(lower: str) -> str | None:
    template = re.search(
        r"(?:which|what) template (?:should i use|to use) (?:for|with) (.+)",
        lower,
    ) or re.search(
        r"(?:suggest|recommend) (?:a )?template (?:for|with) (.+)",
        lower,
    )
    if not template:
        return None
    doc_type = re.sub(r"[?!.]", "", template.group(1)).strip().lower()
    doc_type = re.sub(r"^(a|an|the) ", "", doc_type)
    for tmpl in TEMPLATES:
        label = tmpl["label"].lower()
        tid = tmpl["id"].lower()
        if (
            doc_type in label
            or label in doc_type
            or doc_type in tid
            or tid in doc_type
            or (doc_type == "business letter" and tid == "business_letter")
        ):
            return (
                f"For {doc_type}, you should use the '{tmpl['label']}' template (ID: {tmpl['id']})."
            )
    for doc_type_name, doc_type_obj in _current_document_types().items():
        name_lower = doc_type_name.lower()
        if doc_type in name_lower or name_lower in doc_type:
            template_id = doc_type_obj.default_workflow_template_id or doc_type_obj.template
            return f"For {doc_type_name}, you should use the template with ID: {template_id}."
    return (
        f"I couldn't find a specific template for {doc_type}. You might want to use a "
        "general document template."
    )


def _document_type_question(lower: str) -> str | None:
    if "document types" not in lower and "doc types" not in lower:
        return None
    types = list(_current_document_types().keys())
    if not types:
        return "No document types are currently defined."
    return f"Available document types: {', '.join(types)}."


def _template_list_question(lower: str) -> str | None:
    if "templates" not in lower or ("list" not in lower and "show" not in lower):
        return None
    if not TEMPLATES:
        return "No templates are currently available."
    template_names = [t["label"] for t in TEMPLATES]
    return f"Available templates: {', '.join(template_names)}."


def _response_time_question(lower: str) -> str | None:  # noqa: C901
    pattern1 = (
        r"(?:how long does|how long) (?:it take|does it take) (?:for )?(?:user )?([\w-]+) "
        r"(?:to respond|respond|to review|review)"
    )
    pattern2 = r"(?:how long) (?:does )?([\w-]+) (?:take to respond|respond|to review|review)"
    pattern3 = r"how long does ([\w-]+) take to respond"
    response_time = (
        re.search(pattern1, lower) or re.search(pattern2, lower) or re.search(pattern3, lower)
    )
    if not response_time:
        return None
    user = response_time.group(1)
    user_approvals = [
        a
        for a in approvals.values()
        if a.reviewer == user and a.state == "approved" and a.signed_at
    ]
    if not user_approvals:
        return f"I don't have enough data to determine {user}'s typical response time."
    response_times: list[int] = []
    for approval in user_approvals:
        if approval.due_at and approval.signed_at:
            try:
                signed_at = approval.signed_at
                if isinstance(signed_at, str):
                    signed_at = datetime.fromisoformat(signed_at.replace("Z", "+00:00"))
                if isinstance(signed_at, datetime) and signed_at <= approval.due_at:
                    response_times.append((approval.due_at - signed_at).days)
            except Exception as _dt_exc:
                _logger.debug("Skipping approval response-time entry: %s", _dt_exc)
                continue
    if not response_times:
        return f"I don't have enough data to determine {user}'s typical response time."
    avg_days = sum(response_times) / len(response_times)
    if avg_days < 1:
        return f"{user} typically responds within a day."
    if avg_days < 7:
        return f"{user} typically responds within {round(avg_days)} days."
    weeks = round(avg_days / 7)
    return f"{user} typically responds within {weeks} week{'s' if weeks > 1 else ''}."


STOP_WORDS = {
    "what",
    "where",
    "can",
    "i",
    "find",
    "information",
    "about",
    "the",
    "a",
    "an",
    "docreview360",
    "docreview",
    "in",
    "to",
    "of",
    "and",
    "is",
    "how",
    "do",
}

# Directories that do not contain useful project documentation.  Walking these
# trees (in particular ``node_modules``) is extremely expensive and previously
# caused tests querying repository content to spend tens of seconds scanning
# unrelated files.  Ignoring them keeps lookups fast even in large workspaces.
_SKIP_DIRS = {"node_modules", ".git", "dist", "build", "frontend"}


def _repo_content_question(lower: str, root: Path | None = None) -> str | None:  # noqa: C901
    if "docreview360" not in lower and "docreview" not in lower:
        return None
    words = re.findall(r"[a-z0-9]+", lower)
    keywords = [w for w in words if w not in STOP_WORDS]
    if not keywords:
        return None
    root = root or Path(__file__).resolve().parents[2]
    # Keep track of the "best" match found.  We prefer README files and
    # `pyproject.toml` over `requirements.txt` because they contain richer
    # documentation about dependencies.  Previously the first match returned by
    # ``Path.rglob`` was used which depended on the filesystem traversal order
    # and often surfaced ``requirements.txt`` before ``pyproject.toml``.  Using
    # :func:`os.walk` lets us skip heavy directories up front.
    best_match: Path | None = None
    best_rank = -1
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for filename in filenames:
            path = Path(dirpath) / filename
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".ico"}:
                continue
            # Ignore lock files and other generated artefacts which can be very
            # large and rarely contain helpful documentation.  Without this the
            # search would often return ``poetry.lock`` before ``pyproject.toml``
            # simply because it is encountered first in the directory walk.
            if path.name.lower().endswith(".lock"):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore").lower()
            except Exception as _read_exc:
                _logger.debug("Skipping unreadable file '%s': %s", path, _read_exc)
                continue
            if all(k in text for k in keywords):
                name = path.name.lower()
                if "readme" in name:
                    return (
                        f"I found information about {' '.join(keywords)} in "
                        f"{path.relative_to(root)}."
                    )
                rank = 2 if name == "pyproject.toml" else 1 if name == "requirements.txt" else 0
                if rank > best_rank:
                    best_match = path
                    best_rank = rank
    if best_match:
        return (
            f"I found information about {' '.join(keywords)} in " f"{best_match.relative_to(root)}."
        )
    return f"I couldn't find information about {' '.join(keywords)} in DocReview360."


def _writing_style_question(lower: str) -> str | None:
    if "passive voice" in lower:
        return (
            "Strunk and White recommend using the active voice. Rewrite sentences to "
            "show who performs the action."
        )
    if (
        "strunk and white" in lower
        or "grammar" in lower
        or "writing style" in lower
        or "style guide" in lower
    ):
        return (
            "Follow Strunk and White's 'Elements of Style': use the active voice, "
            "omit needless words, and keep your writing clear and concise."
        )
    return None


def _system_question(lower: str) -> str | None:
    if "what is docreview360" in lower or "what does docreview360 do" in lower:
        return (
            "DocReview360 is a document review and approval workflow system that helps "
            "manage document creation, review, and approval processes."
        )
    if "how does" in lower and "work" in lower:
        return (
            "DocReview360 uses workflows to manage document reviews. Projects are "
            "assigned to users, who then go through approval steps with different "
            "reviewers until the document is finalized."
        )
    return None


async def answer_question(question: str) -> str:
    """Return an answer for ``question`` based on DocReview360 data."""
    if not question.strip():
        raise ValueError("question must not be empty")

    lower = question.lower().strip()
    handlers = [
        _assignment_question,
        _status_question,
        _workload_question,
        _overdue_question,
        _template_question,
        _document_type_question,
        _template_list_question,
        _response_time_question,
        _writing_style_question,
        _repo_content_question,
        _system_question,
    ]
    for handler in handlers:
        response = handler(lower)
        if response:
            return response
    return (
        "I can help answer questions about DocReview360 projects, users, templates, "
        "and document workflows. Try asking about project status, user assignments, "
        "or which template to use for a specific document type."
    )
