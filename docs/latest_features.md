# Latest Features

This page is the canonical record of completed work moved out of
`RELEASE_CHECKLIST.md`.

For open work, use `RELEASE_CHECKLIST.md`.

## Authoring and templates

- TipTap-based structured template authoring is in place.
- TipTap plugin safety and compatibility rules are documented in `docs/tiptap-plugins.md`.
- Content schema validation and CMS-safe persistence are in place.
- Template version history and phase-based locking are available.
- Document type defaults now use workflow templates via `default_workflow_template_id`, and the admin configuration page now reads `GET /workflow-templates` for the Default Workflow selector.
- The 10 built-in document types now seed curated starter HTML instead of the bare `<h1>{name}</h1>` placeholder.
- `GET /document-types/{name}/starter-content` is available for editor bootstrapping with curated document-type HTML.

## Workflow and project review

- Phase configuration now uses richer metadata and DB-backed APIs.
- Document types can define their own ordered workflow phases.
- Project review screens include workflow timeline, approvals grid, reviewer comments, and phase gating.
- Share links, viewer-only access, and branding controls shipped.
- Reviewer assignments now persist with lifecycle state, due dates, replacement tracking, and auto-migration from legacy `reviewers` lists.
- `/users/search` and the debounced `UserPicker` support reviewer assignment from the project view.
- Review notifications now fire for assignment, reminder, question, concurrence, replacement, signature, and all-complete events, and each dispatch is written to the project notification log.
- The feedback ledger now stores feedback type, assignment links, threaded replies, dispositions, progress counts, and phase archives.
- Concurrence gates, non-concurrence, concur-with-comments, internal sign-off, and `review-summary` readiness checks shipped.
- The project view now centers the lifecycle stepper plus Overview, Reviewers, Feedback, Signatures, Approvals, and History tabs, including reviewer-focused banner actions.
- Project lifecycle close-out now covers `draft` through `closed`, published metadata, records-package download with integrity hash, and records status on the Overview tab.
- Reviewer deadlines now support per-assignment due dates, SLA summaries, overdue status badges, reminder runs, and escalation.

## Review and signature

- Documenso is available as the default e-signature provider.
- DocuSign is available as an optional enterprise provider.
- Signature activity is logged into the audit trail.
- Approval-by-initials support shipped.
- Long-term signature validation shipped with RFC 3161 timestamping, OCSP and CRL evidence capture, archival timestamps, stored LTV packages, and `GET /signatures/{id}/ltv`.

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

## Verified on 2026-03-12

- Review lifecycle transitions now emit audit events and lifecycle webhooks across assignment and feedback flows.
- Review-cycle regression coverage now includes the full create → assign → feedback → answer → concur → sign → close → records-package flow plus reviewer replacement preserving ledger history.
- Federal Style Validator backend integration now runs behind `FEDERAL_STYLE_VALIDATOR_URL`; preflight, regulatory, and ML-quality endpoints proxy to FSV with internal fallback, and `GET /fsv/status` exposes config and health state.
- Document quality scoring now persists last score/date/grade plus history, and dashboard KPI cards surface aggregate quality metrics.
- Microsoft 365 co-authoring via WOPI shipped with lock persistence, WOPI host routes, and discovery XML.
- Document conversion now covers RTF, ODT, EPUB, LaTeX, and Confluence wiki-markup export.
- External search configuration now supports SQLite, OpenSearch, or Elasticsearch backends through the stub client, and analytics dashboard/export endpoints shipped.
- Backend locale-preference endpoints (`GET/PUT /users/me/locale`) shipped.
- Built-in plugin toggle state now persists in SQLite, per-organization tool configuration shipped, and grammar/spell plugins are classified under `Community / Optional`.
- `SECURITY.md` now routes vulnerability reports through GitHub private advisories instead of a placeholder email address.
- `CHANGELOG.md` now explicitly follows Keep a Changelog and Semantic Versioning.
- Source distribution packaging now uses `MANIFEST.in` pruning plus explicit setuptools runtime-asset allowlists in `pyproject.toml`.
- Release docs now include `scripts/check-docs-links.py`, `scripts/check-docs-drift.py`, a cross-platform Quick Start in `README.md`, the current `docs/adr/0001-core-architecture.md`, and the FastAPI `/docs` entry point linked from the README.
- Local release automation now includes `scripts/release-shepherd.sh`, artifact-stamped automation reports, `.claude/settings.json` guardrails, `.claude/commands/*`, and the Raspberry Pi-friendly `scripts/headless-loop.sh`.
- Automated triage and release-report loops now cover failing-test clustering, flaky-test ranking, issue grooming, and release-note drafting.
- Automated release audits now cover packaging contents, placeholder scans, dependency/security review, deployment drift, performance regression, accessibility, UX smoke review, audit-log integrity, and ML packaging verification.
- Security review coverage now validates `SECURITY_REVIEW.md`, `SECURITY.md` scan references, password/secrets/encryption docs, OIDC/JWT defaults, and audit-log chain verification.
- Reviewer notification preferences now support per-reviewer channel selection with passing regression coverage.
- Federal Style Validator release docs now include `docs/federal-style-validator.md`, the optional `fedstylevalidator` dependency extra, and documented compatibility and pinning guidance.
- The remaining local FSV duplicate-check surfaces are now explicitly audited in `doc_validation.py`, `document_checker.py`, and `tiptapFederalStyleLint.ts` pending the final plugin cutover.

## Test and quality

- API routes were brought back into coverage measurement.
- The coverage threshold was raised to 80.
- Smoke tests, route-auth tests, role and MFA tests, DB persistence tests, and CLI coverage were expanded.
- Stub cleanup removed the old generated task modules and their test-only scaffolding.
- Broad silent exception handling was replaced with logged failure paths in key modules.
