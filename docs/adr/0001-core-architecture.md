# ADR 0001: Core Architecture

## Status

Accepted (updated 2026-03-12)

## Context

DocReview360 is a document review and approval workflow system for government and regulated-industry
documents. It must support multiple document types, configurable review phases, approval signatures,
audit logging, and multi-tenant access control.

The initial prototype required:
- Rapid iteration without operational overhead
- Clear extension points for enterprise auth (OIDC, LDAP, SAML, CAC/PIV)
- A separation between backend logic and frontend presentation
- Audit-log immutability suitable for compliance workflows

## Decision

### Backend — FastAPI (Python 3.12)

- **Framework**: FastAPI with async endpoints, dependency injection, and Pydantic v2 models.
- **Storage**: SQLite via SQLAlchemy 2.0 (default); PostgreSQL/MSSQL/Oracle via optional extras.
- **Auth**: JWT HS256 + bcrypt + TOTP MFA; optional OIDC/LDAP/SAML/WebAuthn/PIV/CAC.
- **RBAC**: `require_permission()` / `require_role()` FastAPI dependencies in `rbac.py`.
- **Route organization**: All routes in sub-routers under `api/`; `api/__init__.py` only
  registers routers and app-level middleware.
- **Audit log**: Append-only SQLite table with SHA-256 hash chain; `verify_audit_log_chain()`
  in `logs/_query.py`.
- **Celery**: Task queue using `memory://` in dev, Redis in production.
- **ML**: Optional ONNX inference (`ml/onnx_infer.py`); PyTorch training scripts separated.

### Frontend — Next.js / React

- **Framework**: Next.js (pages router) with React 18.
- **Editor**: TipTap (ProseMirror-based) with custom extensions.
- **API calls**: `authenticatedFetch()` helper in `lib/api.ts`; JWT stored in-memory (not localStorage).
- **State**: React Query for server state; local useState for UI state.
- **i18n**: `next-i18next` with locale JSON in `public/locales/` (en/es/fr/de).

### Storage Layout

```
src/docreview360/   backend + CLI source (FastAPI, SQLAlchemy, Celery, ML)
  api/              sub-routers (auth, projects, documents, workflows, admin, …)
  auth/             auth package (_models, _repository, _core)
  logs/             audit log package (_db, _dispatch, _query)
  ml/               ML models and inference
tests/              pytest suite (excluded from published sdist)
frontend/           Next.js application
  pages/            route pages
  components/       reusable React components
  extensions/       TipTap editor extensions
docs/               architecture, deployment, ADRs
scripts/            dev tooling and automation loops
helm/               Kubernetes Helm chart
k8s/                Kubernetes manifests
```

## Alternatives Considered

| Alternative | Reason not chosen |
|-------------|-------------------|
| Django REST | FastAPI's async-native design and Pydantic integration fit better |
| SQLite only | Enterprise requirements needed PostgreSQL/MSSQL support |
| localStorage for JWT | Security: XSS exposure; moved to in-memory + httpOnly cookie |
| Monolithic `api/__init__.py` | Decomposed into sub-routers at ~1,800 lines to stay maintainable |

## Consequences

**Positive:**
- FastAPI dependency injection makes auth/RBAC consistent across all routes.
- SQLite default means zero-config development and Raspberry Pi deployment.
- Sub-router architecture keeps `api/__init__.py` under 2,000 lines.
- Optional extras for PostgreSQL, MSSQL, Oracle, OIDC, LDAP, ML keep the base install lean.

**Negative / mitigations:**
- Python 3.13 not yet supported (PyTorch wheels); mitigated by `requires-python = ">=3.11,<3.13"`.
- In-memory Celery broker unsuitable for production; documented in deployment guide.
- ONNX model files must be bundled separately; ML features degrade gracefully if absent.

## References

- `docs/deployment.md` — production deployment guide
- `docs/supported-platforms.md` — supported OS/Python/Node versions
- `docs/disaster_recovery.md` — backup and restore procedures
- `SECURITY.md` — security policy and vulnerability reporting
- `src/docreview360/api/__init__.py` — router registration
- `src/docreview360/auth/__init__.py` — auth configuration
