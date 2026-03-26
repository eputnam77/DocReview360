from importlib.util import find_spec
from pathlib import Path
from uuid import uuid4

import pytest
from docreview360.document_checker import run_checks


def _has_style_validator() -> bool:
    return find_spec("fedstylevalidator") is not None


if not _has_style_validator():
    pytest.skip("FedStyleValidator validator not installed", allow_module_level=True)


def test_document_checker_runs() -> None:
    root = Path(__file__).resolve().parents[1]
    workspace_tmp = root / ".tmp" / "test-document-checker"
    workspace_tmp.mkdir(parents=True, exist_ok=True)
    f = workspace_tmp / f"doc-{uuid4().hex}.txt"
    f.write_text("hello hello")
    result = run_checks(f)
    assert "grammar" in result
