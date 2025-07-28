# 20250728 - Pin Python Dependencies

## Status
Accepted

## Context
Configuration reviews flagged that our `pyproject.toml` used version ranges
like `>=` which can lead to drift between environments. The AGENTS playbook
recommends pinning dependencies to exact versions and caching the lock file
for deterministic builds.

## Decision

* Pin core dependencies in `pyproject.toml` using exact versions matching the
  `poetry.lock` file.
* Regenerate `poetry.lock` so CI and local installs are consistent.
* Update the CI skeleton to cache based on the lockfile hash which ensures
  cached environments are invalidated when dependencies change.

## Consequences

* Contributors get the same package versions locally and in CI.
* Updates require explicit version bumps in `pyproject.toml` followed by a new
  lock file, making changes auditable.
* Dependency caching remains effective because the key incorporates the
  `poetry.lock` hash.
