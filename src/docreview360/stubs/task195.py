"""Git send-email hook utilities."""

from __future__ import annotations

from pathlib import Path

from ..stubs import record_task_completion


def task195() -> Path:
    """Return the path to the sample hook script.

    The calling code can copy this file to ``.git/hooks/sendemail-validate``
    to enable the optional patch validation hook described in the README.
    """

    record_task_completion(195)
    return Path(__file__).resolve().parents[2] / "scripts" / "sendemail-validate.sample"
