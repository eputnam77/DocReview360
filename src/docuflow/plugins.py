"""Minimal plugin registry used for editors, exporters and validators."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Callable, Dict, Iterable, List


class PluginRegistry:
    """Registry that stores plugin callables by name."""

    def __init__(self) -> None:
        self._plugins: Dict[str, Callable[..., Any]] = {}

    def register(self, name: str, plugin: Callable[..., Any]) -> None:
        """Register a plugin under a unique name."""
        if name in self._plugins:
            raise ValueError(f"Plugin '{name}' already registered")
        self._plugins[name] = plugin

    def get(self, name: str) -> Callable[..., Any]:
        """Retrieve a plugin by name."""
        try:
            return self._plugins[name]
        except KeyError as exc:
            raise KeyError(f"Plugin '{name}' not found") from exc

    def unregister(self, name: str) -> None:
        """Remove a plugin from the registry."""
        try:
            del self._plugins[name]
        except KeyError as exc:
            raise KeyError(f"Plugin '{name}' not found") from exc

    def all(self) -> List[str]:
        """List registered plugin names."""
        return list(self._plugins.keys())


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
        except Exception as exc:  # pragma: no cover - sanity fallback
            raise ImportError(f"Cannot import plugin module {mod_name}") from exc

        register_func = getattr(module, "register", None)
        if not callable(register_func):
            raise ValueError(f"Plugin module {mod_name} lacks a 'register' function")

        register_func(registry)
