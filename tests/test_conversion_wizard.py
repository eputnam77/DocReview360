"""Conversion wizard tests."""

from docreview360.conversion import convert_ac_to_order
from docreview360.documents import DocumentModel


def test_ac_to_policy_conversion_preserves_numbers() -> None:
    doc = DocumentModel(
        id="1",
        content="# 1 Intro\n## 1.1 Purpose\nAdvisory Circular AC-123",
    )
    converted = convert_ac_to_order(doc)
    assert "1.1 Purpose" in converted.content
    assert "ORD-123" in converted.content
