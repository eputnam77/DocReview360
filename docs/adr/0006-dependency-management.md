# 0006 - Dependency and Environment Management

## Status
Accepted

## Context
DocReview360 uses Python 3.12 and ships with multiple language placeholders.
To keep installs reproducible, the project relies on **Poetry** along with
`uv` for virtual environment management. Previous docs mentioned the CI
workflow but not how dependencies are installed.

## Decision
* `poetry.lock` stores all Python dependencies.
* `uv pip sync` installs packages according to the lock file both locally and
  in CI.
* A small `[tool.poetry]` table exists in `pyproject.toml` for Poetry
  compatibility.
* The GitHub Actions workflow installs `uv`, runs `poetry install --sync`, then
  executes `uv pip sync` before the quality gate.

## Consequences
Users following the setup instructions get the exact versions tested in CI,
reducing "works on my machine" problems.
