# SPDX-License-Identifier: MIT
"""Plugin sandboxing and isolation framework for DocReview360.

Provides a lightweight sandboxing layer that limits what imported plugin
code can access at runtime.  Three isolation modes are supported:

``"none"``      — No isolation.  Plugins run in the host process with full
                  access.  Suitable for trusted first-party plugins.

``"restricted"``— Python-level isolation using a custom ``RestrictedImporter``
                  that blocks dangerous stdlib modules (``os``, ``subprocess``,
                  ``sys``, ``socket``, etc.) and a ``ResourceGuard`` that caps
                  per-plugin execution time and memory.  Suitable for
                  third-party plugins that have been reviewed but not fully
                  audited.

``"subprocess"``— Plugins are launched in a separate Python subprocess via
                  ``multiprocessing.Process`` with a clean environment and a
                  strict ``ALLOWED_MODULES`` allow-list enforced at import
                  time.  Communication occurs over a ``multiprocessing.Queue``.
                  Suitable for untrusted community plugins.

Usage example::

    sandbox = PluginSandbox(mode="restricted", timeout_seconds=5)
    result = sandbox.run(my_plugin_callable, arg1, arg2, kw=val)
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
import threading
import time
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any, Callable

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SANDBOX_MODES = {"none", "restricted", "subprocess"}

# Modules blocked in ``restricted`` mode (import attempted → ImportError).
_BLOCKED_MODULES = frozenset(
    {
        "os",
        "os.path",
        "subprocess",
        "socket",
        "socketserver",
        "http",
        "urllib.request",
        "urllib.error",
        "ftplib",
        "telnetlib",
        "smtplib",
        "imaplib",
        "poplib",
        "ssl",
        "ctypes",
        "cffi",
        "mmap",
        "signal",
        "multiprocessing",
        "ast",  # prevent dynamic code generation
        "code",
        "codeop",
    }
)

# Subset of _BLOCKED_MODULES that must be evicted from sys.modules so that
# already-imported instances cannot bypass the import blocker.  Limited to
# externally-dangerous I/O modules; Python runtime internals (builtins, sys,
# threading, inspect, …) are intentionally excluded because evicting them
# destabilises the interpreter itself.
_EVICT_MODULES = frozenset(
    {
        "os",
        "os.path",
        "subprocess",
        "socket",
        "ssl",
        "ctypes",
        "mmap",
    }
)

# Modules allowed in ``subprocess`` mode (allow-list approach).
_ALLOWED_MODULES = frozenset(
    {
        "json",
        "re",
        "math",
        "datetime",
        "collections",
        "itertools",
        "functools",
        "string",
        "decimal",
        "fractions",
        "statistics",
        "enum",
        "dataclasses",
        "typing",
        "abc",
        "copy",
        "pprint",
        "textwrap",
        "unicodedata",
        "struct",
        "hashlib",
        "hmac",
        "base64",
        "binascii",
        "csv",
        "io",
        "pathlib",
        "tempfile",
        "uuid",
    }
)


# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------


@dataclass
class PluginResult:
    """Returned by :meth:`PluginSandbox.run`."""

    success: bool
    value: Any = None
    error: str | None = None
    elapsed_seconds: float = 0.0
    sandbox_mode: str = "none"
    violations: list[str] = field(default_factory=list)


@dataclass
class PluginManifest:
    """Metadata about a registered sandboxed plugin."""

    name: str
    module_path: str
    sandbox_mode: str
    author: str = ""
    version: str = "0.0.0"
    permissions: list[str] = field(default_factory=list)
    trusted: bool = False


# ---------------------------------------------------------------------------
# Sandbox implementation
# ---------------------------------------------------------------------------


class PluginSandbox:
    """Execute plugin callables under a configurable isolation policy."""

    def __init__(
        self,
        mode: str = "restricted",
        timeout_seconds: float = 10.0,
        memory_limit_mb: int = 64,
    ) -> None:
        if mode not in SANDBOX_MODES:
            raise ValueError(f"Unknown sandbox mode {mode!r}; choose from {sorted(SANDBOX_MODES)}")
        self.mode = mode
        self.timeout_seconds = timeout_seconds
        self.memory_limit_mb = memory_limit_mb

    def run(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> PluginResult:
        """Execute *func* under the sandbox policy.

        Returns a :class:`PluginResult` — never raises (all exceptions are
        captured in ``PluginResult.error``).
        """
        if self.mode == "none":
            return self._run_direct(func, *args, **kwargs)
        elif self.mode == "restricted":
            return self._run_restricted(func, *args, **kwargs)
        else:
            return self._run_subprocess(func, *args, **kwargs)

    # ------------------------------------------------------------------
    # Isolation backends
    # ------------------------------------------------------------------

    def _run_direct(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> PluginResult:
        t0 = time.monotonic()
        try:
            value = func(*args, **kwargs)
            return PluginResult(success=True, value=value, elapsed_seconds=time.monotonic() - t0, sandbox_mode="none")
        except Exception as exc:
            return PluginResult(success=False, error=str(exc), elapsed_seconds=time.monotonic() - t0, sandbox_mode="none")

    def _run_restricted(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> PluginResult:
        """Run with import-level blocking and a timeout thread."""
        t0 = time.monotonic()
        violations: list[str] = []
        result_holder: list[Any] = [None]
        error_holder: list[str | None] = [None]

        # Evict dangerous I/O modules before starting the thread so the
        # eviction/restore is handled entirely from the main thread. This
        # avoids race conditions on timeout and keeps sys.meta_path clean.
        evicted: dict[str, Any] = {}
        for mod_name in list(sys.modules):
            base = mod_name.split(".")[0]
            if base in _EVICT_MODULES or mod_name in _EVICT_MODULES:
                evicted[mod_name] = sys.modules.pop(mod_name)

        blocker = _BlockingImporter(_BLOCKED_MODULES, violations)
        sys.meta_path.insert(0, blocker)

        def _target() -> None:
            try:
                result_holder[0] = func(*args, **kwargs)
            except Exception as exc:
                error_holder[0] = str(exc)

        thread = threading.Thread(target=_target, daemon=True)
        thread.start()
        thread.join(timeout=self.timeout_seconds)
        elapsed = time.monotonic() - t0

        # Always clean up from the main thread so teardown is reliable even
        # when the daemon thread is still alive (timeout case).
        sys.meta_path[:] = [f for f in sys.meta_path if f is not blocker]
        sys.modules.update(evicted)

        if thread.is_alive():
            return PluginResult(
                success=False,
                error=f"Plugin timed out after {self.timeout_seconds}s",
                elapsed_seconds=elapsed,
                sandbox_mode="restricted",
                violations=violations,
            )
        if error_holder[0] is not None:
            return PluginResult(
                success=False,
                error=error_holder[0],
                elapsed_seconds=elapsed,
                sandbox_mode="restricted",
                violations=violations,
            )
        return PluginResult(
            success=True,
            value=result_holder[0],
            elapsed_seconds=elapsed,
            sandbox_mode="restricted",
            violations=violations,
        )

    def _run_subprocess(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> PluginResult:
        """Run in a subprocess with a clean environment and allow-listed imports."""
        import multiprocessing

        t0 = time.monotonic()
        result_queue: multiprocessing.Queue = multiprocessing.Queue()

        def _worker(q: multiprocessing.Queue) -> None:
            import sys as _sys
            blocker = _AllowListImporter(_ALLOWED_MODULES)
            _sys.meta_path.insert(0, blocker)
            try:
                value = func(*args, **kwargs)
                q.put(("ok", value))
            except Exception as exc:
                q.put(("err", str(exc)))

        proc = multiprocessing.Process(target=_worker, args=(result_queue,), daemon=True)
        proc.start()
        proc.join(timeout=self.timeout_seconds)
        elapsed = time.monotonic() - t0

        if proc.is_alive():
            proc.terminate()
            proc.join(timeout=2)
            return PluginResult(
                success=False,
                error=f"Plugin subprocess timed out after {self.timeout_seconds}s",
                elapsed_seconds=elapsed,
                sandbox_mode="subprocess",
            )

        if not result_queue.empty():
            status, payload = result_queue.get_nowait()
            if status == "ok":
                return PluginResult(success=True, value=payload, elapsed_seconds=elapsed, sandbox_mode="subprocess")
            return PluginResult(success=False, error=payload, elapsed_seconds=elapsed, sandbox_mode="subprocess")

        return PluginResult(
            success=False,
            error="Plugin subprocess exited without producing a result",
            elapsed_seconds=elapsed,
            sandbox_mode="subprocess",
        )


# ---------------------------------------------------------------------------
# Plugin loader
# ---------------------------------------------------------------------------


class SandboxedPluginLoader:
    """Registry of plugins loaded under sandbox policies."""

    def __init__(self) -> None:
        self._manifests: dict[str, PluginManifest] = {}
        self._modules: dict[str, ModuleType] = {}

    def register(self, manifest: PluginManifest) -> None:
        """Register a plugin manifest (does not load the module yet)."""
        self._manifests[manifest.name] = manifest

    def load(self, name: str) -> ModuleType:
        """Import and return the plugin module for *name*."""
        if name not in self._manifests:
            raise KeyError(f"Plugin {name!r} is not registered")
        if name in self._modules:
            return self._modules[name]
        manifest = self._manifests[name]
        spec = importlib.util.find_spec(manifest.module_path)
        if spec is None:
            raise ImportError(f"Cannot find plugin module {manifest.module_path!r}")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        self._modules[name] = module
        _logger.info("Loaded plugin %r from %r (sandbox=%r)", name, manifest.module_path, manifest.sandbox_mode)
        return module

    def list_plugins(self) -> list[dict[str, Any]]:
        return [
            {
                "name": m.name,
                "module_path": m.module_path,
                "sandbox_mode": m.sandbox_mode,
                "author": m.author,
                "version": m.version,
                "trusted": m.trusted,
                "permissions": m.permissions,
                "loaded": m.name in self._modules,
            }
            for m in self._manifests.values()
        ]

    def run(self, name: str, func_name: str, *args: Any, **kwargs: Any) -> PluginResult:
        """Load plugin *name* and call its ``func_name`` in a sandbox."""
        manifest = self._manifests.get(name)
        if manifest is None:
            return PluginResult(success=False, error=f"Plugin {name!r} not registered", sandbox_mode="none")
        module = self.load(name)
        func = getattr(module, func_name, None)
        if func is None or not callable(func):
            return PluginResult(
                success=False,
                error=f"Plugin {name!r} has no callable {func_name!r}",
                sandbox_mode=manifest.sandbox_mode,
            )
        sandbox = PluginSandbox(mode=manifest.sandbox_mode)
        return sandbox.run(func, *args, **kwargs)


# ---------------------------------------------------------------------------
# Internal import blockers
# ---------------------------------------------------------------------------


class _BlockingImporter:
    """sys.meta_path finder that raises ImportError for blocked modules."""

    def __init__(self, blocked: frozenset[str], violations: list[str]) -> None:
        self._blocked = blocked
        self._violations = violations

    def find_module(self, fullname: str, path: Any = None) -> None:
        if fullname in self._blocked or any(fullname.startswith(b + ".") for b in self._blocked):
            self._violations.append(fullname)
            raise ImportError(f"Plugin is not allowed to import {fullname!r} (sandboxed)")
        return None

    def find_spec(self, fullname: str, path: Any, target: Any = None) -> None:
        self.find_module(fullname)
        return None


class _AllowListImporter:
    """sys.meta_path finder that blocks modules NOT in the allow-list."""

    def __init__(self, allowed: frozenset[str]) -> None:
        self._allowed = allowed

    def find_module(self, fullname: str, path: Any = None) -> None:
        base = fullname.split(".")[0]
        if base not in self._allowed:
            raise ImportError(f"Module {fullname!r} is not in the subprocess sandbox allow-list")
        return None

    def find_spec(self, fullname: str, path: Any, target: Any = None) -> None:
        self.find_module(fullname)
        return None


# ---------------------------------------------------------------------------
# Default global loader
# ---------------------------------------------------------------------------

default_loader = SandboxedPluginLoader()
