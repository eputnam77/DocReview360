import socket
import threading
import time
from typing import Iterator

import pytest
import uvicorn
from playwright.sync_api import Page

from docreview360.api import app


@pytest.fixture(scope="session")
def live_server() -> Iterator[str]:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join()


@pytest.mark.e2e
def test_workflow_end_to_end(page: Page, live_server: str) -> None:
    page.goto(live_server)
    page.fill('input[name="username"]', "admin")
    page.fill('input[name="password"]', "admin")
    page.click('button[type="submit"]')
    page.wait_for_url(live_server + "/projects")

    create = page.request.post(
        live_server + "/workflows",
        data={"project": "e2e", "phases": ["draft", "review"]},
    )
    assert create.ok
    wf_id = create.json()["id"]

    assign = page.request.post(
        live_server + f"/workflows/{wf_id}/assign",
        data={"user": "alice"},
    )
    assert assign.ok
    assert assign.json()["reviewers"] == ["alice"]

    advance = page.request.post(live_server + f"/workflows/{wf_id}/advance")
    assert advance.ok
    assert advance.json()["phase"] == "review"
