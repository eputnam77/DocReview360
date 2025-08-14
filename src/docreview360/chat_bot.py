"""General AI chatbot for DocReview360 content and document writing questions."""

from __future__ import annotations

import re
from datetime import datetime

try:  # pragma: no cover - optional dependency
    from .search import list_projects, overdue_high_priority, projects
except Exception:  # pragma: no cover - search module may depend on pydantic
    projects = {}
    def list_projects(_user: str) -> list:  # pragma: no cover
        return []

    def overdue_high_priority() -> list:  # pragma: no cover
        return []

try:  # pragma: no cover - optional dependency
    from .workflows import workflows
except Exception:  # pragma: no cover - workflows module may depend on pydantic
    workflows = {}

try:  # pragma: no cover - optional dependency
    from .approvals import approvals
except Exception:  # pragma: no cover - approvals module may depend on pydantic
    approvals = {}

try:  # pragma: no cover - optional dependency
    from .doc_types import document_types
except Exception:  # pragma: no cover - doc_types module may depend on pydantic
    document_types = {}

# Define templates data structure based on frontend templates
TEMPLATES = [
    {
        "id": "faa_ac",
        "label": "FAA Advisory Circular (TipTap)",
        "type": "tiptap",
    },
    {
        "id": "demo_tiptap",
        "label": "Demo Memo (TipTap)",
        "type": "tiptap",
    },
    {
        "id": "demo_word",
        "label": "Demo Letter (Word .docx)",
        "type": "word",
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
    }
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
    return f"{proj_id} is currently in the {proj.status} phase."


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
    doc_type = template.group(1)
    for tmpl in TEMPLATES:
        if (
            doc_type.lower() in tmpl["label"].lower()
            or tmpl["label"].lower() in doc_type.lower()
            or doc_type.lower() in tmpl["id"].lower()
            or tmpl["id"].lower() in doc_type.lower()
            or (doc_type.lower() == "business letter" and tmpl["id"] == "business_letter")
        ):
            return (
                f"For {doc_type}, you should use the '{tmpl['label']}' template (ID: {tmpl['id']})."
            )
    for doc_type_name, doc_type_obj in document_types.items():
        if (
            doc_type.lower() in doc_type_name.lower()
            or doc_type_name.lower() in doc_type.lower()
        ):
            template_id = doc_type_obj.default_template_id or doc_type_obj.template
            return f"For {doc_type_name}, you should use the template with ID: {template_id}."
    return (
        f"I couldn't find a specific template for {doc_type}. You might want to use a "
        "general document template."
    )


def _document_type_question(lower: str) -> str | None:
    if "document types" not in lower and "doc types" not in lower:
        return None
    types = list(document_types.keys())
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


def _response_time_question(lower: str) -> str | None:
    pattern1 = (
        r"(?:how long does|how long) (?:it take|does it take) (?:for )?(?:user )?([\w-]+) "
        r"(?:to respond|respond|to review|review)"
    )
    pattern2 = (
        r"(?:how long) (?:does )?([\w-]+) (?:take to respond|respond|to review|review)"
    )
    pattern3 = r"how long does ([\w-]+) take to respond"
    response_time = (
        re.search(pattern1, lower)
        or re.search(pattern2, lower)
        or re.search(pattern3, lower)
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
        return (
            f"I don't have enough data to determine {user}'s typical response time."
        )
    response_times: list[int] = []
    for approval in user_approvals:
        if approval.due_at and approval.signed_at:
            try:
                signed_at = datetime.fromisoformat(
                    approval.signed_at.replace('Z', '+00:00')
                )
                if signed_at <= approval.due_at:
                    response_times.append((approval.due_at - signed_at).days)
            except Exception:
                pass
    if not response_times:
        return (
            f"I don't have enough data to determine {user}'s typical response time."
        )
    avg_days = sum(response_times) / len(response_times)
    if avg_days < 1:
        return f"{user} typically responds within a day."
    if avg_days < 7:
        return f"{user} typically responds within {round(avg_days)} days."
    weeks = round(avg_days / 7)
    return f"{user} typically responds within {weeks} week{'s' if weeks > 1 else ''}."


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
