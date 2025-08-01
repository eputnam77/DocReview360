# mypy: ignore-errors
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
from pytest import TempPathFactory


@pytest.fixture(scope="session")  # type: ignore[misc]
def seeded_config(tmp_path_factory: TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("seedcfg") / "docreview360.yml"
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
            "--seed",
            "--config-path",
            str(path),
        ],
    )
    assert result.exit_code == 0
    sample = Path("samples/ac.md")
    assert sample.exists()
    return path


@pytest.fixture(scope="session")  # type: ignore[misc]
def live_server_seeded(seeded_config: Path) -> Iterator[str]:
    original = cfg.CONFIG_FILE
    cfg.CONFIG_FILE = seeded_config
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
def test_cli_seed_creates_sample(page: Page, live_server_seeded: str) -> None:
    page.goto(live_server_seeded + "/config")
    text = page.text_content("pre")
    assert text is not None and "database" in text
    assert Path("samples/ac.md").exists()
