# CLAUDE.md

Project rules for Claude Code. Full architecture details: `docs/`, `.dev/ADRs/`.

## Commands

### Backend (Python 3.11–3.12; 3.13 not supported)

```bash
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -e ".[dev,test,security]"
pre-commit install

uvicorn docreview360.api:app --reload --host 0.0.0.0 --port 8000

pytest --cov=src
pytest tests/test_approvals.py::test_foo

pre-commit run --all-files
bandit -r src -lll --skip B101
python scripts/run-pip-audit.py

poetry run python scripts/run_e2e.py
```

### Frontend (Node 18+)

```bash
cd frontend && npm install --legacy-peer-deps
echo "NEXT_PUBLIC_API_BASE=http://localhost:8000" > .env.local
npm run dev   # http://localhost:3000
```

### CLI

```bash
docreview360 init
docreview360 migrate export backup.gz
docreview360 migrate import backup.gz
```

## Layout

```
src/docreview360/   backend + CLI (FastAPI, SQLAlchemy, Celery, ML)
tests/              pytest suite
frontend/           Next.js / React (pages/, components/, extensions/)
docs/               architecture, deployment, performance
scripts/            dev tooling
```

Key modules: `api/__init__.py` (all routes), `auth.py`, `rbac.py`, `audit.py`,
`approvals.py`, `workflow_engine.py`, `ml/onnx_infer.py`, `integrations/registry.py`.

Storage: in-memory dicts for v0.1 prototype; SQLite via SQLAlchemy for persistence.
Auth: JWT HS256 + bcrypt + TOTP MFA. RBAC via `require_permission()` dependency.

## Environment

- `DOCREVIEW360_ENV=dev` — skips secret enforcement, seeds demo users
- Demo users: `alice/password` (admin), `bob/password` (auditor)
- `SIGNATURE_PROVIDER=sandbox` (default) or `documenso`
- `DOCREVIEW360_ML_MODEL_DIR` — path to packaged ONNX model

## Code style

- Line length: **100** (Black + Ruff), Python **3.12**, mypy strict
- Bandit skips: B101, B110, B311
- `tests/` and `document_checker.py` excluded from strict mypy
- Commit messages: Conventional Commits (`feat/fix/docs/refactor/test/chore`)
- Release coverage gate: 90% branch coverage (`--cov-fail-under=90`)
- `src/docreview360/api/__init__.py` is very large (hundreds of endpoints) — use Grep or subagent rather than loading it whole
