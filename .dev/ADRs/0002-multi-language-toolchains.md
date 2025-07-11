# 0002 - Multi-language Toolchains

## Status
Accepted

## Context
While DocReview360 is primarily a Python project, some features like the web UI or
performance-critical plugins may benefit from other languages. We want to keep
the repository ready for those additions without forcing them today.

## Decision

* Include minimal configuration files for TypeScript (`tsconfig.json`), Rust
  (`Cargo.toml`), and Go (`go.mod`).
* Each configuration declares the package name `docreview360` and basic compiler
  settings.
* No actual source code is required yet; these files serve as placeholders for
  future scaffolding.

## Consequences

* Developers can immediately start using the respective toolchains if needed.
* Continuous integration will validate these files with `cargo check`, `go vet`,
  or `npm run build` once real code exists.
