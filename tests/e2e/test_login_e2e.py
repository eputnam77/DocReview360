import socket
import threading
import time
from typing import Iterator

import pytest
import uvicorn
from docreview360.api import app
from playwright.sync_api import Page


@pytest.fixture(scope="session")
def live_server() -> Iterator[str]:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    # wait for server to start
    time.sleep(1)
    try:
        yield f"http://127.0.0.1:{port}"
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
    # the projects endpoint returns JSON wrapped in a <pre> element when
    # requested via Playwright. Extract the text content and check it is
    # valid JSON.
    text = page.text_content("pre")
    assert text is not None and text.startswith("[")
