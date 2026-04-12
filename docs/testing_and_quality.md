# Testing and Quality

Use this page for local checks before you commit, package, or release.

## Install development tools

```bash
uv pip install -e ".[dev,test,security]"
pre-commit install
```

## Run the standard local checks

```bash
pre-commit run --all-files
pytest --cov=src
bandit -r src -lll --skip B101
python scripts/run-pip-audit.py
```

## Lint, format, and type checks

`pre-commit run --all-files` runs the standard repository checks, including:

- Ruff
- Black
- Mypy
- Bandit
- mdformat
- Codespell

Use this command before opening a pull request.

## Unit tests and coverage

```bash
pytest --cov=src
```

Release target: `90%` branch coverage.

## Security scans

Code scan:

```bash
bandit -r src -lll --skip B101
```

Dependency scan:

```bash
python scripts/run-pip-audit.py
```

## End-to-end checks

Full suite:

```bash
python scripts/run_e2e.py
```

Smoke gate:

```bash
E2E_REQUIRE_PLAYWRIGHT=1 E2E_TEST_MARK=e2e_smoke python scripts/run_e2e.py
```

Full release gate:

```bash
E2E_REQUIRE_PLAYWRIGHT=1 E2E_TEST_MARK=e2e_full python scripts/run_e2e.py
```

Prerequisites:

- `playwright install`
- Backend and frontend dependencies available locally

Keep artifacts for debugging:

```bash
KEEP_E2E_ARTIFACTS=1 python scripts/run_e2e.py
```

Artifacts are written under `.e2e-runs/<run-id>/`.

## Suggested workflow

1. Run `pre-commit run --all-files`.
2. Run `pytest --cov=src`.
3. Run `bandit -r src -lll --skip B101`.
4. Run `python scripts/run-pip-audit.py`.
5. Run the appropriate E2E command for your change scope.

## Related pages

- [Getting Started](getting_started.md)
- [Developer Guide](developer.md)
- [E2E Guide](e2e.md)
- [Release Packaging](release_packaging.md)
