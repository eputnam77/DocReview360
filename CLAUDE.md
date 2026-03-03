# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend

```bash
# Install (Python 3.11 or 3.12 required; 3.13 not supported due to PyTorch wheels)
uv venv --python 3.12 && source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv pip install -e ".[dev,test,security]"
pre-commit install

# Run backend
uvicorn docreview360.api:app --reload --host 0.0.0.0 --port 8000
# Windows shortcut: pwsh -File scripts/windows/start-backend.ps1

# Tests
pytest --cov=src                              # full suite with coverage
pytest tests/test_approvals.py               # single test file
pytest tests/test_approvals.py::test_foo     # single test

# Linting / type checking (all via pre-commit)
pre-commit run --all-files

# Security
bandit -r src -lll --skip B101
python scripts/run-pip-audit.py

# E2E
poetry run python scripts/run_e2e.py
E2E_REQUIRE_PLAYWRIGHT=1 E2E_TEST_MARK=e2e_smoke poetry run python scripts/run_e2e.py
```

### Frontend (Node 18+)

```bash
cd frontend
npm install --legacy-peer-deps
echo "NEXT_PUBLIC_API_BASE=http://localhost:8000" > .env.local
npm run dev      # http://localhost:3000
```

### CLI wizard

```bash
docreview360 init         # interactive config → docreview360.yaml
docreview360 migrate export backup.gz
docreview360 migrate import backup.gz
```

## Architecture

### Repo layout

```
src/docreview360/    Python package (backend + CLI)
  api/               FastAPI sub-application (approvals, ML, webhooks)
  integrations/      Third-party connectors (SharePoint, signature providers)
  ml/                ONNX/PyTorch pipeline (training, inference, anomaly detection)
  models/            SQLAlchemy ORM models + Pydantic schemas
  migrations/        SQL migration scripts
  templates/         Jinja2 HTML templates
tests/               Pytest suite (unit, integration, E2E)
frontend/            Next.js / React UI (TypeScript)
  pages/             Next.js file-based routes
  components/        Shared React components
  extensions/        Tiptap editor extensions
scripts/             Dev-tooling, E2E runner, performance baseline
docs/                Architecture decisions, deployment, performance baseline
```

### Backend

The backend is a single **FastAPI** app (`src/docreview360/api/__init__.py`) with hundreds of endpoints. It is mounted via `uvicorn docreview360.api:app`.

**Storage model**: Most domain objects (documents, approvals, workflows, comments) are held in **in-memory dicts** (e.g. `documents`, `approvals`, `workflows`) for the v0.1 prototype. Persistence uses SQLite by default through SQLAlchemy (`database.py`) and separate SQLite files for users (`DOCREVIEW360_USER_DB`), RBAC (`DOCREVIEW360_RBAC_DB`), and search state (`DOCREVIEW360_SEARCH_DB`).

**Key modules and their roles:**

| Module | Role |
|---|---|
| `api/__init__.py` | All HTTP routes; imports every other domain module |
| `auth.py` | JWT (HS256) + bcrypt passwords + TOTP MFA; SQLite user store |
| `rbac.py` | Role matrix (SQLite-backed `RoleRepository`); `require_permission()` FastAPI dependency |
| `audit.py` | HMAC-chained audit log entries with WORM semantics |
| `approvals.py` | Approval state machine (`pending→approved/rejected`); digital signature, Celery reminders |
| `documents.py` | In-memory document store; MIME validation; HTML sanitization via bleach |
| `workflow_engine.py` | Sequential/parallel approval step progression on top of `approvals` |
| `workflows.py` / `workflow_components.py` | Workflow template definitions and phase-step UI building blocks |
| `integrations/registry.py` | Provider registry (signature backends: `sandbox`, `documenso`, `local`) |
| `ml/` | PyTorch → ONNX pipeline; `onnx_infer.py` for production inference; `signature_anomaly.py` for anomaly scoring |
| `celery_app.py` | Celery worker configuration (Redis broker); async tasks like approval reminders |
| `plugins.py` | Stevedore-based plugin loader for editors and exporters |
| `cli.py` | Click CLI entrypoint: `docreview360 init`, `ml train/export/package`, `migrate export/import` |

### Authentication flow

1. `POST /token` → returns JWT (uses `auth.py` → `create_access_token`)
2. Bearer token validated per-request by `get_current_user()` FastAPI dependency
3. RBAC checked via `require_permission(permission)` dependency (reads `RoleRepository`)
4. OIDC flow available at `/oidc/token` / `/oidc/me` with separate key config
5. CSRF protection via `X-CSRF-Token` header matching `csrf_token` cookie when using HTTP-only cookies

### ML pipeline

Training produces PyTorch weights → `docreview360 ml export` converts to ONNX (opset 18, dynamic axes) → `docreview360 ml package` stages artifacts. `DOCREVIEW360_ML_MODEL_DIR` points the running API at a package. Inference runs via `ml/onnx_infer.py` with `CPUExecutionProvider` by default.

### Frontend

Next.js 13+ pages-router app. Pages live under `frontend/pages/`. Shared components in `frontend/components/`. The editor is Tiptap with custom extensions in `frontend/extensions/`. Communicates with the backend exclusively via `NEXT_PUBLIC_API_BASE`.

### Environment

- `DOCREVIEW360_ENV=dev` (empty/dev/test) skips secret enforcement and enables demo user seeding.
- Set non-dev value (e.g. `production`) to require all secrets at startup.
- Demo users: `alice/password` (admin), `bob/password` (auditor).
- `SIGNATURE_PROVIDER=sandbox` is the default; set to `documenso` for Documenso callbacks to `POST /hooks/documenso`.

### API versioning

All existing endpoints remain at root (`/`). Versioned aliases available at `/api/v1/*`.

### Code style

- Line length: **100** (Black + Ruff)
- Python target: **3.12**
- Mypy strict mode; `tests/` and `document_checker.py` are excluded from strict checks
- Bandit skips: B101, B110, B311
