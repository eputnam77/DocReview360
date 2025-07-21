"""HID Global PIV/CAC login stub (Task 220)."""

from __future__ import annotations

from ..stubs import record_task_completion


def piv_cac_login(certificate: bytes) -> bool:
    """Validate PIV/CAC certificate and return authentication result."""
    if not isinstance(certificate, (bytes, bytearray)) or not certificate:
        raise ValueError("certificate data required")

    record_task_completion(220)
    # Stub validation: any non-empty certificate is accepted
    return True
