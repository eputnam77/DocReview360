"""Command line interface for DocuFlow configuration wizard."""

from __future__ import annotations

from pathlib import Path

import click

from .config import CONFIG_FILE, Config


@click.group()
def cli() -> None:
    """Main CLI entrypoint for all commands."""
    # The function body intentionally does nothing; ``click`` uses it as a
    # command group.  Having an explicit function makes the entry point clearer.
    return None


@cli.command()
@click.option(
    "--database",
    type=click.Choice(["postgres", "mysql", "sqlite"], case_sensitive=False),
    prompt=True,
)
@click.option(
    "--editor",
    type=click.Choice(["tiptap"], case_sensitive=False),
    default="tiptap",
    show_default=True,
    prompt=True,
)
@click.option(
    "--cms",
    type=click.Choice(["none", "local"], case_sensitive=False),
    default="none",
    show_default=True,
    prompt=True,
)
@click.option(
    "--auth",
    type=click.Choice(["oidc"], case_sensitive=False),
    default="oidc",
    show_default=True,
    prompt=True,
)
@click.option("--host", default="127.0.0.1", show_default=True, prompt=True)
@click.option("--port", type=int, default=8000, show_default=True, prompt=True)
@click.option("--debug/--no-debug", default=False, show_default=True, prompt=True)
@click.option(
    "--seed/--no-seed",
    default=False,
    help="Create sample document type files after writing config",
)
@click.option(
    "--config-path",
    type=click.Path(dir_okay=False, writable=True),
    default=str(CONFIG_FILE),
    show_default=True,
)
def init(
    database: str,
    editor: str,
    cms: str,
    auth: str,
    host: str,
    port: int,
    debug: bool,
    seed: bool,
    config_path: str,
) -> None:
    """Interactive configuration wizard.

    Parameters
    ----------
    database:
        Selected database backend.
    editor:
        Preferred document editor.
    cms:
        CMS integration option.
    auth:
        Authentication provider.
    seed:
        When ``True`` a sample Advisory Circular markdown file is created.
    """
    if not (0 < port < 65536):
        raise click.BadParameter("Port must be between 1 and 65535")

    config = Config(
        database=database,
        editor=editor,
        cms=cms,
        auth=auth,
        host=host,
        port=port,
        debug=debug,
    )
    path = Path(config_path)
    try:
        config.save(path)
        click.echo(f"Configuration written to {path}")
        if seed:
            from .seeds import seed_sample_ac

            sample_path = seed_sample_ac()
            click.echo(f"Sample document written to {sample_path}")
    except OSError as exc:
        raise click.ClickException(f"Failed to write config: {exc}") from exc


if __name__ == "__main__":
    cli()
