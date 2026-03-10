# Release Completed Items

This page archives completed release work that was removed from `RELEASE_CHECKLIST.md`
on 2026-03-10.

Use this page as the implementation record.
Use `RELEASE_CHECKLIST.md` as the open backlog.

## Product work completed

- TipTap-based authoring, template versioning, template locking, and CMS-safe content validation shipped.
- Phase metadata and document type workflows moved to DB-backed models and APIs.
- Project workflow timeline, approvals table, reviewer comments, share links, viewer role, and branding controls shipped.
- Documenso and DocuSign integrations shipped behind the shared signature provider interface.
- Inline comments, structured tags, comment disposition workflow, comment export, document conversion, and revision diff support shipped.
- Audit snapshots, immutable audit logging, exportable audit packages, RBAC matrix views, and verification override logging shipped.
- AI-assisted review features shipped for style validation, acronyms, headings, plain language, regulatory citation checks, and pre-flight validation.
- Multi-tenant organizations, per-organization settings, API keys, notifications, project bundle export/import, and backup/restore support shipped.
- Health endpoint, deterministic migrations, demo data, dev Docker Compose, production deployment guide, version history, restore, freeze, and automatic document versioning shipped.

## Architecture and persistence work completed

- Approvals, workflow instances, phases, document types, and webhook subscriptions moved to database-backed persistence.
- Workflow phase configuration and document type workflow APIs were aligned around richer DB-backed schemas.
- Route auth coverage was expanded across admin, workflow, document, dashboard, AI, search, API key, and share-link surfaces.
- CORS hardening and non-SQLite connection pooling were added.
- The API module was split into domain routers and the approvals code was split into a package.
- High-risk global state paths gained explicit locking.

## Auth and security work completed

- JWT session invalidation via token generation counters shipped.
- Logout support and previous-key JWT rotation support shipped.
- Public route audits and targeted auth-guard fixes shipped for plugins, AI key access, and search stats.
- Security headers, CSP headers, safer frontend token handling, safer redirect handling, and authenticated WebSocket log access shipped.
- Audit HMAC key rotation support and purge resilience shipped.

## Test and quality work completed

- API routes were brought back into coverage measurement.
- Coverage threshold was raised to 80.
- Smoke tests, route-auth tests, role and MFA tests, DB persistence tests, and CLI test coverage were expanded.
- Stub cleanup removed the old generated task modules and their test-only scaffolding.
- Broad silent exception handling was replaced with logged failure paths in key modules.

## Packaging and release engineering completed

- Packaging metadata was consolidated on PEP 621 and setuptools.
- Build and `twine check` validation were completed successfully.
- CLI metadata, changelog, project URLs, classifiers, and entry points were cleaned up.
- The project license was migrated from GPL-3.0-only to MIT, with PostgreSQL support moved to optional extras.
- UI build metadata footer support was added for release packaging.

## Supporting docs already in place

- `docs/tiptap-plugins.md`
- `docs/ai-optimization-prompts.md`
- `docs/deployment.md`
- `docs/observability.md`
- `docs/security/key-rotation.md`
- `docs/release_packaging.md`
- `docs/cli.md`
