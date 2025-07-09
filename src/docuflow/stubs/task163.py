"""Implementation for task 163."""

from ..stubs import record_task_completion

EXTENSIONS = ["Bold", "Italic", "Heading", "BulletList"]


def render_extension_menu(enabled: list[str] | None = None) -> str:
    """Return HTML snippet for the extension toggle menu."""
    record_task_completion(163)
    enabled = enabled or []
    items = "\n".join(
        f"<input type='checkbox' name='{ext}' {'checked' if ext in enabled else ''}/>{ext}"
        for ext in EXTENSIONS
    )
    return f"<div id='extension-menu'>\n{items}\n</div>"
