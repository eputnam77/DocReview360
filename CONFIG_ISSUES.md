# Configuration Issues

## Unpinned Dependencies Detected

The following manifests contain version specifiers that are not fully pinned:

- `frontend/package.json` and `frontend/package-lock.json` use caret (`^`) ranges for numerous dependencies.
- `pyproject.toml` specifies versions using `>=` ranges instead of exact versions.

This conflicts with the policy that all dependencies must be pinned (no `*`, `^`, `latest`).

## Recommended Actions

- Replace caret (`^`) version ranges in `package.json` and `package-lock.json` with exact versions.
- Pin Python dependencies in `pyproject.toml` using exact versions to maintain reproducible builds.

Once these adjustments are made, re-run `poetry check --lock` or `pip-compile --dry-run` to confirm there is no drift.
