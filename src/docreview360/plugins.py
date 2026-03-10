# SPDX-License-Identifier: MIT
"""Minimal plugin registry used for editors, exporters and validators."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Callable, Dict, Iterable, List


class PluginRegistry:
    """Registry that stores plugin callables by name with enable/disable support."""

    def __init__(self) -> None:
        self._plugins: Dict[str, Callable[..., Any]] = {}
        self._disabled: set[str] = set()

    def register(self, name: str, plugin: Callable[..., Any], *, enabled: bool = True) -> None:
        """Register a plugin under a unique name.

        Parameters
        ----------
        name:
            Unique plugin identifier.
        plugin:
            Callable implementing the plugin.
        enabled:
            Whether the plugin should start enabled.
        """
        # Normalize and validate the name to avoid accidentally creating entries
        # keyed by empty strings or incidental whitespace.  Previously a name of
        # ``""`` or ``"  "`` would be accepted and stored, making the plugin
        # impossible to manage via ``enable``/``disable`` calls which expect a
        # meaningful identifier.
        name = name.strip()
        if not name:
            raise ValueError("Plugin name cannot be empty")
        if name in self._plugins:
            raise ValueError(f"Plugin '{name}' already registered")
        self._plugins[name] = plugin
        if not enabled:
            self._disabled.add(name)

    def get(self, name: str) -> Callable[..., Any]:
        """Retrieve a plugin by name ensuring it is enabled."""
        if name in self._disabled:
            raise ValueError(f"Plugin '{name}' is disabled")
        try:
            return self._plugins[name]
        except KeyError as exc:
            raise KeyError(f"Plugin '{name}' not found") from exc

    def unregister(self, name: str) -> None:
        """Remove a plugin from the registry."""
        try:
            del self._plugins[name]
            self._disabled.discard(name)
        except KeyError as exc:
            raise KeyError(f"Plugin '{name}' not found") from exc

    def enable(self, name: str) -> None:
        """Enable a previously disabled plugin."""
        if name not in self._plugins:
            raise KeyError(f"Plugin '{name}' not found")
        self._disabled.discard(name)

    def disable(self, name: str) -> None:
        """Disable a plugin without removing it."""
        if name not in self._plugins:
            raise KeyError(f"Plugin '{name}' not found")
        self._disabled.add(name)

    def all(self) -> List[str]:
        """List registered plugin names."""
        return list(self._plugins.keys())

    def info(self) -> List[dict[str, Any]]:
        """Return plugin metadata for management APIs."""
        return [{"name": name, "enabled": name not in self._disabled} for name in self._plugins]


registry = PluginRegistry()


def load_plugins(modules: Iterable[str]) -> None:
    """Import modules and register their plugins.

    Each module must define a ``register`` function accepting the global
    :class:`PluginRegistry` instance. Errors during import or registration are
    raised with helpful context.
    """

    for mod_name in modules:
        try:
            module = import_module(mod_name)
        except Exception as exc:
            raise ImportError(f"Cannot import plugin module {mod_name}") from exc

        register_func = getattr(module, "register", None)
        if not callable(register_func):
            raise ValueError(f"Plugin module {mod_name} lacks a 'register' function")

        register_func(registry)
