# Contributing

## Scope

Contributions should improve reliability, security, usability, and maintainability of DocReview360.

## Workflow

1. Open an issue describing the problem and proposed change.
2. Create a focused branch and include tests for behavior changes.
3. Run local checks before opening a PR:
   - `pytest -q`
   - `ruff check src tests`
4. Submit a PR with a clear summary, risks, and test evidence.

## Standards

- Keep changes minimal and reversible.
- Prefer explicit errors over silent fallback behavior.
- Do not introduce secrets, credentials, or private data.
- Update documentation when behavior changes.

## Governance

Repository maintainers review and merge changes.
Security-sensitive changes may require additional review and verification before merge.

## Conduct

By participating, you agree to follow the Code of Conduct in `CODE_OF_CONDUCT.md`.
