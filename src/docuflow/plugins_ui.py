"""Minimal HTML rendering for plugin management (task 32)."""

from __future__ import annotations

from .plugins import registry


def render_plugin_table() -> str:
    """Return an HTML table listing plugins and their enabled state."""
    rows = []
    for info in registry.info():
        status = "enabled" if info["enabled"] else "disabled"
        rows.append(f"<tr><td>{info['name']}</td><td>{status}</td></tr>")
    return "<table>" + "".join(rows) + "</table>"
