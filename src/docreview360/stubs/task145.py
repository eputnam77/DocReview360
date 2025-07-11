"""Implementation for task 145."""

from ..plugin_marketplace import install_plugin


def task145(name: str) -> None:
    """Install a plugin."""

    install_plugin(name)
    return None
