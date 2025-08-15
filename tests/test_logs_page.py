from pathlib import Path


def test_logs_page_contains_websocket() -> None:
    # Use path relative to project root
    project_root = Path(__file__).parent.parent
    content = (project_root / "frontend" / "pages" / "logs" / "index.tsx").read_text()
    assert "wsProtocol" in content
    assert "wss" in content
