import threading
import time
from typing import Iterator

import pytest
from playwright.sync_api import Page
import uvicorn

from docreview360.api import app


@pytest.fixture(scope="session")
def live_server() -> Iterator[str]:
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    # wait for server to start
    time.sleep(1)
    try:
        yield "http://127.0.0.1:8000"
    finally:
        server.should_exit = True
        thread.join()


@pytest.mark.e2e
def test_login_flow(page: Page, live_server: str) -> None:
    page.goto(live_server)
    page.fill('input[name="username"]', "admin")
    page.fill('input[name="password"]', "admin")
    page.click('button[type="submit"]')
    page.wait_for_url(live_server + "/projects")
    assert page.url.endswith("/projects")
    assert page.content().startswith("[")
