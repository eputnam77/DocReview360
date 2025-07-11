"""Plugin loader orchestrator used by the editor (Task 102)."""

from __future__ import annotations

from typing import Callable, Iterable, List


def load_plugins(loaders: Iterable[Callable[[], str]]) -> List[str]:
    """Run plugin loader callables and return plugin names.

    If any loader raises an exception the error is propagated. This
    simplified orchestrator allows unit tests to verify that all
    wrappers activate successfully.
    """
    names: List[str] = []
    for loader in loaders:
        name = loader()
        if not isinstance(name, str):
            raise TypeError("loader must return plugin name")
        names.append(name)
    return names
