from click.testing import CliRunner
from docuflow.cli import cli
from docuflow.config import CONFIG_FILE


def test_init_writes_config() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli,
            [
                "init",
                "--database",
                "sqlite",
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
