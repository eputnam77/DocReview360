# mypy: ignore-errors
import threading
import time
from typing import Iterator

import pytest
import uvicorn
from docreview360.api import app
from playwright.sync_api import Page


@pytest.fixture(scope="session")  # type: ignore[misc]
def live_server() -> Iterator[str]:
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1)
    try:
        yield "http://127.0.0.1:8000"
    finally:
        server.should_exit = True
        thread.join()


@pytest.mark.e2e
def test_approval_lifecycle(page: Page, live_server: str) -> None:
    page.goto(live_server)
    page.fill('input[name="username"]', "admin")
    page.fill('input[name="password"]', "admin")
    page.click('button[type="submit"]')
    page.wait_for_url(live_server + "/projects")

    wf = page.request.post(
        live_server + "/workflows",
        data={"project": "e2e", "phases": ["draft", "review"]},
    )
    assert wf.ok
    wf_id = wf.json()["id"]

    create = page.request.post(
        live_server + "/approvals",
        data={"workflow": wf_id, "reviewer": "alice"},
    )
    assert create.ok
    appr_id = create.json()["id"]

    update = page.request.put(
        f"{live_server}/approvals/{appr_id}",
        data={"state": "approved", "signature": "signed"},
    )
    assert update.ok
    assert update.json()["state"] == "approved"

    fetch = page.request.get(f"{live_server}/approvals/{appr_id}")
    assert fetch.ok
    assert fetch.json()["signature"] == "signed"
