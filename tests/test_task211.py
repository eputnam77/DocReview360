from typing import Any, Dict

from docreview360.stubs.task211 import task211


def test_task211_store_template() -> None:
    """Template should be added to store."""

    store: Dict[str, Any] = {}
    result = task211(store, "hello", "hi")
    assert result["hello"] == "hi"
