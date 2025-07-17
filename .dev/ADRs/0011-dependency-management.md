# 0011 - Dependency and Environment Management

## Status
Accepted

## Context
Earlier ADRs documented the repository layout and CI workflow but did not explain how
Python dependencies are installed or how contributors should set up their local
environment. The AGENTS playbook recommends using **Poetry** with **uv** for
reproducible installs across Linux and GitHub Actions.

## Decision

* Manage Python packages with **Poetry** and keep `poetry.lock` as the single
  source of truth.
* Use `uv` to create virtual environments and synchronise dependencies via
  `uv pip sync pyproject.toml` so local installs match the lock file.
* Include a minimal `[tool.poetry]` section in `pyproject.toml` for
  compatibility while still using PEP 621 metadata.
* Update the CI workflow to install `uv`, run `poetry install` followed by
  `poetry sync`, then execute `uv pip sync pyproject.toml`.
* Developers enable pre‑commit hooks after setting up the environment.

## Consequences

* Local environments and CI share the exact package versions defined in
  `poetry.lock`.
* New contributors have a clear setup process using `uv` and Poetry.
* CI jobs run faster thanks to `uv` caching and consistent dependency resolution.
