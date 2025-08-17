"""Seed initial document templates."""

from docreview360.template_manager import upload_template

FAA_AC_TEMPLATE = (
    "<h1 style=\"text-align:center; margin-bottom:0\">Advisory Circular</h1>"
    "<p>This is a seed template.</p>"
)


def run() -> None:
    """Store starter templates using the template manager."""
    upload_template(
        "faa_ac",
        FAA_AC_TEMPLATE.encode("utf-8"),
        {"label": "FAA Advisory Circular", "type": "tiptap"},
    )
