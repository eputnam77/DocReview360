# 20250731 - Repository Baseline and CI Caching

## Status
Accepted

## Context
The project backlog calls for a unified monorepo with a Python backend and
Next.js frontend. Dependencies were only partially pinned and the CI workflow
needed a caching strategy.

## Decision
* Adopt the directory layout described in `NEW_STRUCTURE.md`. Key folders are
  `src/`, `tests/`, `frontend/`, `plugins/`, `iac/`, `monitoring/`, `migrations/`,
  `scripts/`, `.github/` and `.dev/`.
* Manage Python packages with **Poetry** and keep `poetry.lock` under version
  control. All runtime dependencies are pinned to exact versions in
  `pyproject.toml`.
* The GitHub Actions workflow installs dependencies via Poetry and caches both
  the Poetry cache and `.venv` directory using a key derived from
  `poetry.lock`.
* SQL migration files live in the `migrations/` folder and are applied by a
  lightweight `Database.migrate()` helper.

## Consequences
* Contributors have a consistent structure for backend, frontend and ops code.
* CI runs quickly because cached environments only refresh when the lockfile
  changes.
* Pinning versions keeps development reproducible across machines and in CI.
