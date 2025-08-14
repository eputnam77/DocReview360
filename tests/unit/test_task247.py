from typing import Any, Dict

from docreview360.stubs.task247 import apply_watermark


def test_task247_overlay() -> None:
    doc: Dict[str, Any] = {"content": []}
    result = apply_watermark(doc, "sample")
    assert result.get("watermark") == "sample"
