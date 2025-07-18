# 0008 - Plugin Architecture Overview

## Status
Accepted

## Context
DocReview360 exposes optional editors, exporters and validators. A lightweight plugin registry exists in the codebase but the design rationale should be documented for users browsing the public ADRs.

## Decision
- Use a central `PluginRegistry` storing plugin callables by name.
- Plugins register themselves via a `register(registry)` function imported by `load_plugins()`.
- Optional plugins may live under `src/docreview360/plugins/` or be discovered via configuration.

## Consequences
The application can be extended without altering the core package. Plugins written in other languages can integrate via Python bindings or RPC while reusing the same registry.
