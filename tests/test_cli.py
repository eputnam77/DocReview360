from click.testing import CliRunner

from docuflow.cli import CONFIG_FILE, cli


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
            ],
        )
        assert result.exit_code == 0
        assert CONFIG_FILE.exists()
        assert "database" in CONFIG_FILE.read_text()
