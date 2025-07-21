# 0005 - Plugin System Architecture

## Status
Accepted

## Context
The project requires a flexible mechanism to extend editors, exporters and validation logic without changing core code. A light‑weight plugin registry already exists in `src/docreview360/plugins.py`, but the rationale has not been documented.

## Decision
* Adopt a central `PluginRegistry` that stores plugin callables by name and tracks their enabled or disabled state.
* Expose a `load_plugins()` helper that imports modules providing a `register(registry)` function. This keeps plugin code decoupled from the core package.
* Encourage optional plugins to live under `src/docreview360/plugins/` or separate packages discovered via configuration.
* Document plugin configuration in the README and provide basic tests covering registration and toggling.

## Consequences
* Editors, exporters and validators can be added or removed without modifying the main application logic.
* Future language specific plugins (Rust, TypeScript) can hook into the same registry via Python bindings or RPC.
* The architecture stays small and easy to reason about while supporting custom extensions.
