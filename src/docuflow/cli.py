"""Command line interface for DocuFlow configuration wizard."""

from __future__ import annotations

from pathlib import Path

import click
import yaml

CONFIG_FILE = Path("docuflow.yaml")


@click.group()
def cli() -> None:
    """Main CLI entrypoint."""
    pass


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
def init(database: str, editor: str, cms: str, auth: str) -> None:
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
    """
    config = {"database": database, "editor": editor, "cms": cms, "auth": auth}
    try:
        CONFIG_FILE.write_text(yaml.safe_dump(config))
        click.echo(f"Configuration written to {CONFIG_FILE}")
    except OSError as exc:
        raise click.ClickException(f"Failed to write config: {exc}") from exc


if __name__ == "__main__":
    cli()
