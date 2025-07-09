"""Central message templates for audit logs."""

from datetime import datetime

MESSAGES = {
    "create_project": "{user} created project {project_id} on {date} at {time}",
    "import_docx": "{user} imported DOCX file '{filename}' to project {project_id} on {date}",
    "upload_file": "{user} uploaded file '{filename}' to project {project_id} on {date}",
    "convert_tiptap": "System converted DOCX to TipTap format for project {project_id} on {date}",
    "login": "{user} logged into system on {date}",
}


def render(name: str, **data: str) -> str:
    """Return a formatted message by name."""
    template = MESSAGES.get(name, name)
    now = datetime.utcnow()
    data.setdefault("date", now.strftime("%Y-%m-%d"))
    data.setdefault("time", now.strftime("%H:%M"))
    return template.format(**data)
