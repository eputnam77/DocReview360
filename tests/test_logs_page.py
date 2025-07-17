from pathlib import Path


def test_logs_page_contains_websocket() -> None:
    content = Path("frontend/pages/logs/index.tsx").read_text()
    assert "ws://" in content
