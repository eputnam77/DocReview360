# 0007 - Multi-language Toolchains

## Status
Accepted

## Context
The project primarily uses Python but anticipates future extensions written in TypeScript, Rust and Go. Early ADRs in `.dev/ADRs/` describe placeholder configuration files, yet the public docs did not summarise why they exist.

## Decision
- Keep minimal config files `tsconfig.json`, `Cargo.toml` and `go.mod` at the repository root so contributors can immediately start using the respective toolchains.
- Each file declares the package name `docreview360` with sane defaults but contains no actual source code.
- Continuous integration will invoke `npx tsc --noEmit`, `cargo check` and `go vet` once real modules appear.

## Consequences
The monorepo stays ready for cross-language components without forcing extra dependencies today. New features can be implemented in the best suited language while sharing a single workflow.
