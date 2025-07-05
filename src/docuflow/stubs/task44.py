"""Implementation for task 44."""

from ..security_compliance import generate_compliance_pdf
from . import record_task_completion


def task44() -> bytes:
    """Generate a sample compliance PDF and return its bytes."""
    data = generate_compliance_pdf("sample flow")
    record_task_completion(44)
    return data
