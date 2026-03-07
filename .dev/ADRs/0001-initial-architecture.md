# ADR 0001: Initial Architecture

## Status
Accepted

## Context
DocReview360 is a document review and approval system requiring a clear architecture
to support multiple document types, workflow phases, approvals, and audit logging.

## Decision
- **Backend**: FastAPI (Python 3.12) with in-memory dicts for v0.1 prototype and
  SQLite via SQLAlchemy for persistence.
- **Frontend**: Next.js / React with TipTap editor integration.
- **Auth**: JWT HS256 + bcrypt password hashing + TOTP MFA.
- **RBAC**: Role-based access control via `require_permission()` dependency.
- **Storage layout**: `src/docreview360/` (backend), `frontend/` (Next.js), `tests/` (pytest).

## Consequences
- Simple in-memory storage allows rapid prototyping without a database dependency.
- SQLite persistence layer provides durable storage for production use.
- FastAPI dependency injection makes auth and permission checking consistent.
