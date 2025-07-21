# 0001 - Initial Architecture and Folder Layout

## Status
Accepted

## Context
DocReview360 is a new project with minimal code. We need a structure that separates
source code from development assets and prepares for multi-language components.

## Decision

* Use **Python** as the primary backend, placing packages under `src/docreview360`.
* Store tests in `tests/` and documentation in `docs/`.
* Keep development workflow files in `.dev/` so they're excluded from
  distribution packages.
* Place continuous integration workflows under `.github/workflows/`.
* Provide a configuration placeholder for TypeScript (`tsconfig.json`) to
  support future extensions.

## Consequences

* Package discovery in `pyproject.toml` uses `setuptools` with
  `packages.find` pointing at `src` and excluding `.dev*` and test folders.
* Future contributors know where to place code for each language.
* The repository is ready for Python packaging and additional toolchains.
