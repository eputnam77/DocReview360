# Latest Features

This page is the canonical record of completed work moved out of
`RELEASE_CHECKLIST.md`.

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
- Audit snapshots, immutable audit logging, exportable audit packages, and verification override logging shipped.

## Release readiness

- v0.1 release scope is fixed around GitHub releases, PyPI packages, and Docker images; docs remain in-repo via `README.md` and `docs/`.
- Release verification scope is full stack across the API, frontend, workers, packaging, and deployment surfaces.
- Packaging metadata was consolidated on PEP 621 and setuptools.
- Build validation and `twine check` completed successfully.
- CLI metadata, changelog metadata, project URLs, classifiers, and entry points were cleaned up.
- Docker builds now use a dedicated `.dockerignore` that excludes repo metadata, tests, caches, local DBs, and local JSON state.
- Docker OCI metadata now advertises the MIT license.
- UI build metadata footer support was added for release packaging.
- Repository ignore rules now cover current local-only E2E artifacts, runtime JSON stores, and generated frontend workflow-template state.

## Security and integration hardening

- Access-token revocation now persists in the auth database, and revoked bearer tokens are rejected during request auth.
- JWT session invalidation via token generation counters shipped.
- Keycloak OIDC support now validates ID tokens against provider JWKS, maps realm and client roles through `keycloak_auth.py`, and applies those roles during the `/oidc/callback` login flow.
- Logout support and previous-key JWT rotation support shipped.
- Workflow templates now persist via `workflow_template_records`; the file-based workflow-template path was removed from runtime docs and examples.
- Protected frontend pages now use `authenticatedFetch(...)`; the remaining shared-hook and utility-path cleanup stays tracked in `RELEASE_CHECKLIST.md`.
- Runtime `filelock` usage was removed from published dependency metadata.
- Plugin marketplace admin flows now expose built-in plugin status and toggle endpoints used by the frontend tools UI.
- Route auth coverage was expanded across admin, workflow, document, dashboard, AI, search, API key, and share-link surfaces.
- Security headers, CSP headers, safer frontend token handling, safer redirect handling, and authenticated WebSocket log access shipped.
- Audit HMAC key rotation support and purge resilience shipped.

## Architecture and operations

- Document branch and merge flows shipped for parallel review tracks.
- Approvals, workflow instances, phases, document types, and webhook subscriptions now persist in the database.
- Duplicate API route registrations were removed from the router-managed backend surfaces; those endpoints are now assembled through FastAPI sub-routers, while singleton health, branding, and websocket endpoints remain directly on `app`.
- `auth`, `search`, `workflows`, `doc_types`, and `documents` were decomposed into packages with backward-compatible `__init__.py` re-exports.
- `logs` and `reporting` were decomposed into packages while preserving public imports through `__init__.py` re-exports.
- Frontend server state now uses React Query with shared `useProjects`, `useDocuments`, `useNotifications`, and `useSessions` hooks; the remaining page-level fetch flows were migrated onto those shared paths.
- YAML-backed configuration modules now share atomic load/save helpers via `yaml_loader.py`.
- CORS hardening and non-SQLite connection pooling shipped.
- High-risk global state paths now use explicit locking.
- The MIT license migration is in place: transitive dependency audit, SPDX headers across `src/docreview360/`, updated `docs/licenses-report.md`, and no incompatible vendored code under `src/`.
- Enterprise authentication shipped across OIDC/OAuth PKCE, LDAP/AD role mapping, SAML, CAC/PIV, WebAuthn, password policy controls, JIT provisioning, SCIM, session hardening, and separation-of-duties enforcement.
- Multi-tenant data isolation and database hardening shipped with org scoping, PostgreSQL RLS, schema-per-tenant support, Alembic setup, SQL Server and Oracle URLs, connection-pooling controls, column encryption, retention policies, audit-log chaining, and encrypted backup guidance.
- Deployment assets now include multi-stage non-root Docker, Helm, Kubernetes manifests, split health probes, reverse-proxy guidance, Redis-backed rate limiting, structured JSON logging, OpenTelemetry wiring, air-gap guidance, production Docker Compose, blue-green rollout docs, and a disaster-recovery runbook.
- Compliance work shipped for FIPS and FedRAMP/FISMA documentation, audit-log completeness checks, NARA metadata, legal holds, eDiscovery export, accessibility scanning, internationalization, and configurable branding and terminology overrides.
- Enterprise integrations and extensibility shipped for SharePoint uploads, Confluence, Google Drive, WebSocket proxy guidance, plugin sandboxing, API versioning guidance, hierarchical configuration, per-organization feature flags, signed lifecycle webhooks, custom workflows, and custom fields.

## Test and quality

- API routes were brought back into coverage measurement.
- The coverage threshold was raised to 80.
- Smoke tests, route-auth tests, role and MFA tests, DB persistence tests, and CLI coverage were expanded.
- Stub cleanup removed the old generated task modules and their test-only scaffolding.
- Broad silent exception handling was replaced with logged failure paths in key modules.
