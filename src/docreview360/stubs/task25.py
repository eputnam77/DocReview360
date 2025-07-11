"""Digital signature helpers for task 25."""

from ..security_utils import create_signature, verify_signature


def task25(data: str) -> bool:
    """Sign and immediately verify the payload."""
    sig = create_signature(data)
    return verify_signature(data, sig)
