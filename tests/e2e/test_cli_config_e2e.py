import threading
import time
from pathlib import Path
from typing import Iterator

import pytest
import uvicorn
from click.testing import CliRunner
from docreview360 import config as cfg
from docreview360.api import app
from docreview360.cli import cli
from playwright.sync_api import Page


@pytest.fixture(scope="session")
def config_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("config") / "docreview360.yml"
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "init",
            "--database",
            "sqlite",
            "--database-url",
            "sqlite:///test.db",
            "--editor",
            "tiptap",
            "--cms",
            "none",
            "--auth",
            "oidc",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--config-path",
            str(path),
        ],
    )
    assert result.exit_code == 0
    assert path.exists()
    return path


@pytest.fixture(scope="session")
def live_server(config_file: Path) -> Iterator[str]:
    original = cfg.CONFIG_FILE
    cfg.CONFIG_FILE = config_file
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
        cfg.CONFIG_FILE = original


@pytest.mark.e2e
def test_cli_init_and_config(page: Page, live_server: str) -> None:
    page.goto(live_server + "/config")
    text = page.text_content("pre")
    assert text is not None and "database" in text
