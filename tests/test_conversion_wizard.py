"""Conversion wizard tests."""

# mypy: ignore-errors

import importlib.util
import sys
import types
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "docreview360"
pkg = types.ModuleType("docreview360")
pkg.__path__ = [str(PACKAGE_DIR)]
sys.modules.setdefault("docreview360", pkg)

spec_conv = importlib.util.spec_from_file_location(
    "docreview360.conversion", PACKAGE_DIR / "conversion.py"
)
conversion = importlib.util.module_from_spec(spec_conv)
sys.modules["docreview360.conversion"] = conversion
spec_conv.loader.exec_module(conversion)

spec_docs = importlib.util.spec_from_file_location(
    "docreview360.documents", PACKAGE_DIR / "documents.py"
)
documents = importlib.util.module_from_spec(spec_docs)
sys.modules["docreview360.documents"] = documents
spec_docs.loader.exec_module(documents)

convert_ac_to_order = conversion.convert_ac_to_order
DocumentModel = documents.DocumentModel


def test_ac_to_policy_conversion_preserves_numbers() -> None:
    doc = DocumentModel(
        id="1",
        content="# 1 Intro\n## 1.1 Purpose\nAdvisory Circular AC-123",
    )
    converted = convert_ac_to_order(doc)
    assert "1.1 Purpose" in converted.content
    assert "ORD-123" in converted.content
