# 20250724 - CI Skeleton and Lockfile Caching

## Status
Accepted

## Context
The initial CI workflow only installed dependencies directly from
`requirements.txt` and lacked caching. Pre-commit hooks and the full
development gate were not executed, leading to slow runs and potential
drift from local environments.

## Decision

* Use **GitHub Actions** to run the dev gate on each push and PR.
* Cache the `.venv` directory and Poetry cache using a key derived from
  `poetry.lock` to avoid rebuilding the environment when dependencies
  have not changed.
* Install dependencies via `poetry install --with dev` so tooling and
  tests share the same lockfile.
* Execute Ruff, Black, MyPy, Bandit and Pytest as defined in the
  playbook.

## Consequences

* CI runs faster thanks to dependency caching.
* The workflow mirrors local development commands, reducing surprises.
* Any lockfile change automatically invalidates the cache to ensure
  clean installs when dependencies update.
