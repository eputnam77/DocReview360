# Testing and quality

Run these checks locally before you commit, package, or release.

## Install the tooling

```bash
uv pip install -e ".[dev,test,security]"
pre-commit install
```

## Before every pull request

```bash
pre-commit run --all-files
pytest --cov=src
bandit -r src -lll --skip B101
python scripts/run-pip-audit.py
```

Then run the end-to-end command that matches your change scope, described below.

## What each check covers

| Command | Covers |
| --- | --- |
| `pre-commit run --all-files` | Ruff, Black, Mypy, Bandit, mdformat, Codespell |
| `pytest --cov=src` | Unit and integration tests with coverage |
| `bandit -r src -lll --skip B101` | Python code security scan |
| `python scripts/run-pip-audit.py` | Dependency vulnerability scan |

Run a single test with `pytest tests/test_approvals.py::test_foo`.

Release target: **90% branch coverage** (`--cov-fail-under=90`).

## End-to-end tests

Install browsers once:

```bash
playwright install
```

Then pick the scope you need:

| Scope | Command |
| --- | --- |
| Everything available locally | `python scripts/run_e2e.py` |
| Pre-merge smoke gate | `E2E_REQUIRE_PLAYWRIGHT=1 E2E_TEST_MARK=e2e_smoke python scripts/run_e2e.py` |
| Full release gate | `E2E_REQUIRE_PLAYWRIGHT=1 E2E_TEST_MARK=e2e_full python scripts/run_e2e.py` |

E2E tests need backend and frontend dependencies installed locally.

To keep artifacts for debugging:

```bash
KEEP_E2E_ARTIFACTS=1 python scripts/run_e2e.py
```

Artifacts land in `.e2e-runs/<run-id>/`.

## Frontend tests

```bash
cd frontend
npm test
npm run build
```

Run both after any frontend change.

## Related pages

- [Get started](getting_started.md)
- [Developer guide](developer.md)
- [E2E guide](e2e.md)
- [Test determinism](test_determinism.md)
- [Release packaging](release_packaging.md)
