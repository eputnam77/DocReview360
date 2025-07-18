from pathlib import Path

from click.testing import CliRunner

from docreview360.cli import cli
from docreview360.config import CONFIG_FILE


def test_init_writes_config() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
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
                "0.0.0.0",
                "--port",
                "8080",
                "--debug",
            ],
        )
        assert result.exit_code == 0
        assert CONFIG_FILE.exists()
        data = CONFIG_FILE.read_text()
        assert "database" in data
        assert "0.0.0.0" in data
        assert "8080" in data


def test_init_rejects_bad_port() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
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
                "0.0.0.0",
                "--port",
                "70000",
            ],
        )
        assert result.exit_code != 0


def test_init_with_seed() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
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
                "0.0.0.0",
                "--port",
                "8080",
                "--seed",
            ],
        )
        assert result.exit_code == 0
        sample = Path("samples/ac.md")
        assert sample.exists()
