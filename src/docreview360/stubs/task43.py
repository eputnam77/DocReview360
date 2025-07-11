"""Implementation for task 43."""

from ..auth import authenticate_mfa
from . import record_task_completion


def task43() -> bool:
    """Return ``True`` if MFA authentication succeeds for default user."""
    user = authenticate_mfa("alice", "password", "123456")
    record_task_completion(43)
    return user is not None
