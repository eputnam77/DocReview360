import pytest

from docreview360.stubs.task201 import task201


@pytest.mark.asyncio
async def test_task201_chat_bot() -> None:
    """Chatbot should answer simple queries."""

    result = await task201("who is assigned to unknown")
    assert "unknown" in result or "not found" in result
