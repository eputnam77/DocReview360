"""Simple plugin registry for editors, exporters and validators."""

from __future__ import annotations

from typing import Any, Callable, Dict, List


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

    def all(self) -> List[str]:
        """List registered plugin names."""
        return list(self._plugins.keys())


registry = PluginRegistry()
