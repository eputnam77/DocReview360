"""General AI chat bot for DocReview360 content and document writing questions."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import List

try:  # pragma: no cover - optional dependency
    from .search import projects, overdue_high_priority, list_projects
except Exception:  # pragma: no cover - search module may depend on pydantic
    projects = {}

try:  # pragma: no cover - optional dependency
    from .workflows import workflows, list_workflows
except Exception:  # pragma: no cover - workflows module may depend on pydantic
    workflows = {}

try:  # pragma: no cover - optional dependency
    from .approvals import list_approvals, approvals
except Exception:  # pragma: no cover - approvals module may depend on pydantic
    approvals = {}

try:  # pragma: no cover - optional dependency
    from .doc_types import document_types, get_document_type
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


async def answer_question(question: str) -> str:
    """Return an answer for ``question`` based on DocReview360 data."""
    if not question.strip():
        raise ValueError("question must not be empty")

    lower = question.lower().strip()
    
    # Handle project assignment questions
    who = re.search(r"who is assigned to (?:project )?([\w-]+)", lower)
    if who:
        proj_id = who.group(1)
        proj = projects.get(proj_id)
        if proj is None:
            return f"Project {proj_id} not found."
        user = proj.temp_user or proj.user
        if user:
            return f"{user} is assigned to {proj_id}."
        return f"No user assigned to {proj_id}."
    
    # Handle project status questions
    status = re.search(r"(?:what is the )?status of (?:project )?([\w-]+)", lower)
    if status:
        proj_id = status.group(1)
        proj = projects.get(proj_id)
        if proj is None:
            return f"Project {proj_id} not found."
        
        # Get workflow status if available
        if proj.workflow:
            wf = workflows.get(proj.workflow)
            if wf:
                return f"{proj_id} is currently in the {wf.phase.lower()} phase."
        
        # Fallback to project status
        return f"{proj_id} is currently in the {proj.status} phase."
    
    # Handle user workload questions
    workload = re.search(r"what is (?:the )?workload (?:for )?(?:user )?([\w-]+)", lower)
    if not workload:
        workload = re.search(r"how many (?:projects|items) (?:are )?(?:assigned to )?(?:user )?([\w-]+)", lower)
    if workload:
        user = workload.group(1)
        user_projects = list_projects(user)
        count = len(user_projects)
        if count == 0:
            return f"{user} has no projects assigned."
        elif count == 1:
            return f"{user} has 1 project assigned."
        else:
            return f"{user} has {count} projects assigned."
    
    # Handle overdue projects question
    if "overdue" in lower and ("project" in lower or "high priority" in lower):
        overdue = overdue_high_priority()
        count = len(overdue)
        if count == 0:
            return "There are no overdue high priority projects."
        elif count == 1:
            return "There is 1 overdue high priority project."
        else:
            return f"There are {count} overdue high priority projects."
    
    # Handle template questions
    template = re.search(r"(?:which|what) template (?:should i use|to use) (?:for|with) (.+)", lower)
    if not template:
        template = re.search(r"(?:suggest|recommend) (?:a )?template (?:for|with) (.+)", lower)
    if template:
        doc_type = template.group(1)
        # Try to find a matching template
        for tmpl in TEMPLATES:
            if (doc_type.lower() in tmpl["label"].lower() or
                tmpl["label"].lower() in doc_type.lower() or
                doc_type.lower() in tmpl["id"].lower() or
                tmpl["id"].lower() in doc_type.lower() or
                (doc_type.lower() == "business letter" and tmpl["id"] == "business_letter")):
                return f"For {doc_type}, you should use the '{tmpl['label']}' template (ID: {tmpl['id']})."
        
        # Try to match with document types
        for doc_type_name, doc_type_obj in document_types.items():
            if doc_type.lower() in doc_type_name.lower() or doc_type_name.lower() in doc_type.lower():
                template_id = doc_type_obj.default_template_id or doc_type_obj.template
                return f"For {doc_type_name}, you should use the template with ID: {template_id}."
        
        return f"I couldn't find a specific template for {doc_type}. You might want to use a general document template."
    
    # Handle document type questions
    if "document types" in lower or "doc types" in lower:
        types = list(document_types.keys())
        if not types:
            return "No document types are currently defined."
        return f"Available document types: {', '.join(types)}."
    
    # Handle template listing questions
    if "templates" in lower and ("list" in lower or "show" in lower):
        if not TEMPLATES:
            return "No templates are currently available."
        template_names = [t["label"] for t in TEMPLATES]
        return f"Available templates: {', '.join(template_names)}."
    
    # Handle user response time questions
    response_time = re.search(r"(?:how long does|how long) (?:it take|does it take) (?:for )?(?:user )?([\w-]+) (?:to respond|respond|to review|review)", lower)
    if not response_time:
        response_time = re.search(r"(?:how long) (?:does )?([\w-]+) (?:take to respond|respond|to review|review)", lower)
    if not response_time:
        response_time = re.search(r"how long does ([\w-]+) take to respond", lower)
    if response_time:
        user = response_time.group(1)
        # Look for approvals by this user to estimate response time
        user_approvals = [a for a in approvals.values() if a.reviewer == user and a.state == "approved" and a.signed_at]
        if not user_approvals:
            return f"I don't have enough data to determine {user}'s typical response time."
        
        # Calculate average response time (simplified)
        response_times = []
        for approval in user_approvals:
            if approval.due_at and approval.signed_at:
                # Parse the signed_at timestamp
                try:
                    signed_at = datetime.fromisoformat(approval.signed_at.replace('Z', '+00:00'))
                    if signed_at <= approval.due_at:
                        response_times.append((approval.due_at - signed_at).days)
                except Exception:
                    pass
        
        if not response_times:
            return f"I don't have enough data to determine {user}'s typical response time."
        
        avg_days = sum(response_times) / len(response_times)
        if avg_days < 1:
            return f"{user} typically responds within a day."
        elif avg_days < 7:
            return f"{user} typically responds within {round(avg_days)} days."
        else:
            weeks = round(avg_days / 7)
            return f"{user} typically responds within {weeks} week{'s' if weeks > 1 else ''}."
    
    # Handle general questions about the system
    if "what is docreview360" in lower or "what does docreview360 do" in lower:
        return "DocReview360 is a document review and approval workflow system that helps manage document creation, review, and approval processes."
    
    if "how does" in lower and "work" in lower:
        return "DocReview360 uses workflows to manage document reviews. Projects are assigned to users, who then go through approval steps with different reviewers until the document is finalized."
    
    # Default response
    return "I can help answer questions about DocReview360 projects, users, templates, and document workflows. Try asking about project status, user assignments, or which template to use for a specific document type."
