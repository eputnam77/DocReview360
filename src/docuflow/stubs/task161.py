"""Implementation for task 161."""

from ..stubs import record_task_completion
from ..workflow_components import MOCK_INSTANCE, UploadDropzone

_ = MOCK_INSTANCE


def render_start_page(workflow_id: str) -> str:
    """Return HTML for a start workflow page."""

    record_task_completion(161)
    dropzone = UploadDropzone().render()
    return f"<form id='start-{workflow_id}'>{dropzone}</form>"
