"""HID Global PIV/CAC login stub (Task 220)."""

from __future__ import annotations

from ..stubs import record_task_completion


def piv_cac_login(certificate: bytes) -> bool:
    """Validate PIV/CAC certificate and return authentication result."""
    record_task_completion(220)
    raise NotImplementedError("task 220 not implemented")
