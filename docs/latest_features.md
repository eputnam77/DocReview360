# Latest Features

This page tracks implemented product work that was moved out of
`RELEASE_CHECKLIST.md` on 2026-03-10 and 2026-03-11.

For open work, use `RELEASE_CHECKLIST.md`.

## Authoring and templates

- TipTap-based structured template authoring is in place.
- TipTap plugin safety and compatibility rules are documented in `docs/tiptap-plugins.md`.
- Content schema validation and CMS-safe persistence are in place.
- Template version history and phase-based locking are available.

## Workflow and project review

- Phase configuration now uses richer metadata and DB-backed APIs.
- Document types can define their own ordered workflow phases.
- Project review screens include workflow timeline, approvals grid, reviewer comments, and phase gating.
- Share links, viewer-only access, and branding controls shipped.

## Review and signature

- Documenso is available as the default e-signature provider.
- DocuSign is available as an optional enterprise provider.
- Signature activity is logged into the audit trail.
- Approval-by-initials support shipped.

## Review experience

- Threaded comments, structured comment tags, and comment dispositions shipped.
- Comment export to Word is available.
- Document conversion supports Word, Markdown, and PDF flows.
- Revision diff and version restore flows are available.

## Dashboards and AI review

- User, manager, admin, executive, reviewer workload, SLA, and document aging views shipped.
- The global footer now shows product and build metadata.
- AI-assisted review shipped for style validation, acronyms, headings, plain language, regulatory citation checks, and pre-flight validation.

## Enterprise readiness

- Organization support and per-organization settings shipped.
- API key management shipped.
- Notification integrations shipped for Slack, Teams, email, and webhooks.
- Project bundle export/import and backup/restore support shipped.

## Platform stability

- Health checks, deterministic migrations, demo data, and the dev Docker Compose stack shipped.
- Document version incrementing, history, restore, and freeze-at-approval shipped.

## Release readiness

- v0.1 release scope is fixed around GitHub releases, PyPI packages, and Docker images; docs remain in-repo via `README.md` and `docs/`.
- Release verification scope is full stack across the API, frontend, workers, packaging, and deployment surfaces.
- Docker builds now use a dedicated `.dockerignore` that excludes repo metadata, tests, caches, local DBs, and local JSON state.
- Docker OCI metadata now advertises the MIT license.
- Repository ignore rules now cover current local-only E2E artifacts, runtime JSON stores, and generated frontend workflow-template state.

## Security and integration hardening

- Access-token revocation now persists in the auth database, and revoked bearer tokens are rejected during request auth.
- Workflow templates now persist via `workflow_template_records`; the file-based workflow-template path was removed from runtime docs and examples.
- Protected frontend pages now use `authenticatedFetch(...)`; raw `fetch(...)` is limited to login and Next.js API routes.
- Runtime `filelock` usage was removed from published dependency metadata.
- Plugin marketplace admin flows now expose built-in plugin status and toggle endpoints used by the frontend tools UI.

## Architecture and operations

- Document branch and merge flows shipped for parallel review tracks.
- `logs` and `reporting` were decomposed into packages while preserving public imports through `__init__.py` re-exports.
- Frontend server state now uses React Query with shared `useProjects`, `useDocuments`, `useNotifications`, and `useSessions` hooks; the remaining page-level fetch flows were migrated onto those shared paths.
- YAML-backed configuration modules now share atomic load/save helpers via `yaml_loader.py`.
- The MIT license migration is in place: transitive dependency audit, SPDX headers across `src/docreview360/`, updated `docs/licenses-report.md`, and no incompatible vendored code under `src/`.
- Enterprise authentication shipped across OIDC/OAuth PKCE, LDAP/AD role mapping, SAML, CAC/PIV, WebAuthn, password policy controls, JIT provisioning, SCIM, session hardening, and separation-of-duties enforcement.
- Multi-tenant data isolation and database hardening shipped with org scoping, PostgreSQL RLS, schema-per-tenant support, Alembic setup, SQL Server and Oracle URLs, connection-pooling controls, column encryption, retention policies, audit-log chaining, and encrypted backup guidance.
- Deployment assets now include multi-stage non-root Docker, Helm, Kubernetes manifests, split health probes, reverse-proxy guidance, Redis-backed rate limiting, structured JSON logging, OpenTelemetry wiring, air-gap guidance, production Docker Compose, blue-green rollout docs, and a disaster-recovery runbook.
- Compliance work shipped for FIPS and FedRAMP/FISMA documentation, audit-log completeness checks, NARA metadata, legal holds, eDiscovery export, accessibility scanning, internationalization, and configurable branding and terminology overrides.
- Enterprise integrations and extensibility shipped for SharePoint uploads, Confluence, Google Drive, WebSocket proxy guidance, plugin sandboxing, API versioning guidance, hierarchical configuration, per-organization feature flags, signed lifecycle webhooks, custom workflows, and custom fields.
