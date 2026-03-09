# AGENTS.md

Authoritative playbook for this repository's OpenAI Codex workflow.
This file is aligned with repo Claude configuration (`CLAUDE.md`, `.claude/settings*.json`, `.claudeignore`).

## 1) Environment And Tooling

- Shell: use repo-local shell commands; prefer minimal, reproducible commands.
- Python: 3.11-3.12 supported. Python 3.13 is not supported.
- Primary env setup:

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev,test,security]"
pre-commit install
```

- Backend run:

```bash
uvicorn docreview360.api:app --reload --host 0.0.0.0 --port 8000
```

- Frontend run:

```bash
cd frontend
npm install --legacy-peer-deps
echo "NEXT_PUBLIC_API_BASE=http://localhost:8000" > .env.local
npm run dev
```

- CLI examples:

```bash
docreview360 init
docreview360 migrate export backup.gz
docreview360 migrate import backup.gz
```

## 2) Core Validation Workflow

- Python edits: run `ruff format` then `ruff check` (or `ruff check --fix`) on touched files.
- Frontend TS/JS edits under `frontend/`: run `npm run lint` in `frontend/`.
- Baseline checks for feature work:

```bash
ruff check src tests
pytest -q
```

- Release-oriented checks (when applicable):

```bash
pytest --cov=src --cov-branch
pytest --cov=src --cov-branch --cov-report=term --cov-fail-under=90
mkdocs build --strict
pytest -q -m e2e
```

- Security/quality commands used by this repo:

```bash
pre-commit run --all-files
bandit -r src -lll --skip B101
python scripts/run-pip-audit.py
mutmut run
trivy fs .
```

## 3) Safety And Permissions Policy

- Never run destructive operations unless explicitly requested.
- Explicitly prohibited by Claude config and mirrored here:
  - `git push`
  - `git reset --hard`
  - `rm -rf`
- Protected file patterns: require explicit user approval before editing:
  - `migrations/*.sql`
  - `.env` files
  - `uv.lock`
  - `poetry.lock`

## 4) Scope And Context Hygiene

- Prefer `search -> read small sections -> summarize`; avoid loading very large files wholesale.
- `src/docreview360/api/__init__.py` is very large; use targeted search instead of full-file reads.
- Respect `.claudeignore` intent when gathering context. Avoid unnecessary reads from:
  - `node_modules/`, `build/`, `dist/`, `.git/`, `.venv/`
  - caches and artifacts such as `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `htmlcov/`, `site/`
  - generated/local data such as `*.db`, `coverage.xml`, `frontend/.next/`

## 5) Workflow Conventions

- For tasks touching 3+ files, draft a brief plan before implementation.
- Keep a short working memory note for long tasks (decisions, changed files, remaining work, test commands).
- Commit style: Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).

## 6) Project Layout Reference

```text
src/docreview360/   backend + CLI (FastAPI, SQLAlchemy, Celery, ML)
tests/              pytest suite
frontend/           Next.js / React
docs/               architecture, deployment, performance
scripts/            development tooling
```

Key modules: `api/__init__.py`, `auth.py`, `rbac.py`, `audit.py`, `approvals.py`, `workflow_engine.py`, `ml/onnx_infer.py`, `integrations/registry.py`.
