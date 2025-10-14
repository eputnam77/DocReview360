# DocReview360 — Product Requirements Document

*Revision: July 8, 2025*

---

## 1. Product Overview

DocReview360 is an end-to-end workspace for drafting, reviewing, approving, and publishing regulated documentation. The platform unifies a FastAPI backend, a React/Next.js frontend, and a Click-based CLI so teams can ingest source files, collaborate in rich editors, run approvals with digital signatures, and surface analytics without leaving a single system.

### 1.1 Core Product Objectives

1. **Accelerate document cycles** by providing rich editors, template automation, and guardrails that maintain formatting and numbering fidelity.
2. **Deliver accountable approvals** through structured workflows, auditable signatures, and immutable log trails.
3. **Expose live operational insight** by aggregating search, dashboards, and workload analytics across projects.
4. **Support modular adoption** via configurable integrations, pluggable extensions, and environment-aware settings.

### 1.2 Experience Pillars

| Pillar | Implementation Highlights |
| --- | --- |
| Editing & Collaboration | TipTap-based editor with autosave and revision history, optional Yjs collaboration, inline comments, and document watchers. |
| Workflow & Approvals | Workflow templates, parallel/sequential phases, Celery-backed reminders/escalations, Documenso (and sandbox) signature providers. |
| Search & Analytics | SQLite-backed project catalog with FTS, saved searches, ranker utilities, dashboards with charts, websocket streams, and CSV exports. |
| Governance & Security | Role-aware FastAPI endpoints, audit log hash chain, RBAC CLI, signature verification, export guardrails, and configurable retention policies. |

---

## 2. Personas & Permission Model

Role management is backed by a SQLite store with defaults seeded for rapid demos. Permissions can be extended through `settings.yaml` or the CLI.

| Role | Primary Permissions | Typical Responsibilities |
| --- | --- | --- |
| **Admin** | create, read, update, delete, edit_field_x, view_audit_log, verification_override | Configure environments, manage templates, override approvals, run integrity tooling. |
| **Manager** | create, read, update | Allocate projects, monitor dashboards, adjust priorities. |
| **SME** | read, edit_field_x | Draft subject-matter content, respond to review feedback. |
| **Reviewer** | read | Participate in approval steps, leave review comments. |
| **Editor** | read, update | Maintain document content, convert uploads, trigger exports. |
| **Observer/User** | read | Monitor project status, download public artefacts. |
| **Auditor** | view_audit_log | Inspect audit streams, verify retention policies. |
| **Verifier** | verification_override | Re-run or force signature verification jobs. |

Role assignments persist in `docreview360_roles.db`, can be edited with `docreview360 rbac-admin`, and are cached per request to reduce store lookups.

---

## 3. End-to-End Workflow

1. **Project creation** – Projects capture name, type, workflow request, priority, and optional temporary assignments. Numbers are generated automatically while respecting user-supplied document numbers.
2. **Template alignment** – Document types link to phase lists and default editor templates. Configurable defaults bootstrap Advisory Circulars, Orders, Manuals, and more.
3. **Document ingestion** – Users upload DOCX/PDF/HTML/Markdown files. The backend sanitises content, extracts text via pluggable pipelines, and stores revision history with SHA-256 hashes.
4. **Collaboration & editing** – TipTap sessions autosave, version content, and optionally broadcast Yjs updates over websockets when `y_py` is installed. Inline comments, mentions, emoji codes, and rate limits keep dialogue structured.
5. **Workflow orchestration** – Workflow templates seed role-specific approval steps. Reviewers are assigned manually or through automation, and each phase transition updates dashboards and assignments.
6. **Approvals & signatures** – Approvals link directly to document revisions, enforce ordering, and integrate with Documenso/sandbox providers for e-sign. Signature callbacks update audit trails and verification state.
7. **Publication & archiving** – Exports respect file-size guardrails, naming templates, and optional guardrail callbacks. Public document lists expose read-only copies with provenance metadata. Archiving jobs can be scheduled for purge windows.
8. **Analytics & follow-up** – Dashboards, saved searches, audit logs, and workload reports keep stakeholders informed. Websocket feeds push updates to live UI panels.

---

## 4. Document & Template Management

### 4.1 Document Types
- Persisted in `document_types.json` with optimistic locking and feature-flagged persistence controls.
- Each type defines an ordered list of workflow phases and optionally binds to a stored editor template for first-open loading.
- Import/export utilities serialise types to JSON with file locks to avoid concurrent write corruption.

### 4.2 Templates
- Templates are stored via the template manager with approval/retirement states, metadata, and retrieval of latest versions.
- Seed data includes an FAA Advisory Circular TipTap template to ease first-run demos.
- Template uploads can originate from JSON, HTML, or DOCX files and are versioned in the backing store.

### 4.3 Document Lifecycle
- Allowed MIME types default to Markdown, HTML, JSON, PDF, and DOCX; administrators can extend or tighten the list and upload size limit through `settings.yaml`.
- Ingestion pipelines are pluggable per MIME type; built-ins cover DOCX (python-docx) and optionally PDF (pdfminer/pypdf) when enabled.
- Every revision appends to an in-memory history, logs an audit event, re-indexes search and FTS stores, and flags documents needing re-review when diffs exceed similarity thresholds.
- Revision history exposes download/diff hooks for future UI surfaces and feeds the public document report API.

### 4.4 File Naming & Export Policies
- Config-driven filename templates (`{id}`, `{number}`) support deterministic exports.
- Size guardrails per format raise warnings and log structured events when exceeded.
- Custom guardrail callbacks can reject exports containing prohibited content before streams are released.

---

## 5. Editing, Collaboration & Feedback

### 5.1 Editors
- TipTap is the primary in-browser editor; ONLYOFFICE and Office Online embeds are supported via editor preference toggles.
- Autosave routes call `autosave_document`, avoiding redundant revisions when content is unchanged.
- Users can switch editor preference per document, enabling hybrid experiences.

### 5.2 Real-Time Collaboration
- `/collab/{doc_id}` websocket broadcasts Yjs updates between connected clients when `y_py` is installed; otherwise, clients receive a dependency error.
- The backend persists raw Yjs updates alongside revisions for reconciliation.

### 5.3 Comments & Mentions
- Comments store raw text, sanitised HTML-safe versions, mentions, emoji shortcuts, and optional parent IDs for threading.
- Configurable length and rate limits prevent spam; administrators can tune limits or disable them entirely.
- API responses always return sanitised comment bodies and describe the allowed formatting contract.

### 5.4 Watchlists & Notifications
- Users can toggle project watch status; watchlists persist to `watchlist.json` (path configurable via `DOCREV_WATCHLIST_FILE`).
- Message templates drive email/chat payloads for project lifecycle events (creation, review requests, escalations, AI assistance). Templates accept contextual placeholders (`{project_id}`, `{user}`, `{date}`) and are centralised for reuse.

---

## 6. Workflow & Approval Management

### 6.1 Workflow Templates
- Library of named templates (branch coordination, pre-coordination, fast-track, etc.) with strictly validated approval order values.
- Each template enumerates role descriptions, required flags, and order numbers; validation logs misconfigurations before they reach runtime.
- Workflows are created per project, track phases, store callback URLs, and register automation bots via a pluggable callback registry.

### 6.2 Approval Records
- Approvals capture reviewer, role, order, due dates, reminders, escalation targets, signature provider metadata, and delegates.
- Creation automatically links approvals to workflow documents, logging audit entries and enforcing immutability controls.
- Celery tasks (`docreview360.approval_reminder`, `docreview360.approval_escalation`) log reminder/escalation events for pending approvals.
- Signature validation supports retries, certificate downloads, and policy fallbacks controlled through settings and environment flags.

### 6.3 Workflow Progression
- Advancing a workflow updates the active phase and notifies registered bots.
- Starting a workflow auto-imports a seed document (Markdown by default) if none exists and rebinds approvals to the new document ID.
- Reviewer assignments avoid duplicates and can be toggled via REST endpoints.

---

## 7. Search, Saved Views & Analytics

### 7.1 Project Catalog
- SQLite-backed repository tracks projects, workflow references, priorities, assignments, and audit timestamps.
- Helpers compute derived fields such as `phase`, `status`, `progress`, and `created_at` for UI compatibility.
- Temporary assignments expire automatically based on configured windows.

### 7.2 Search & Ranking
- Full-text indexing (fts) maintains document content for keyword search.
- Ranked search utilities combine query parsing, scoring, and filter pipelines.
- Saved searches persist query definitions per user with usage counters and review flags.

### 7.3 Dashboards & Reports
- `dashboard_data`, `widget_counts`, and role-specific dashboards (user, manager, admin) surface counts, pending approvals, and health metrics.
- CSV endpoints support exporting summary, throughput, and workload datasets.
- Throughput charts aggregate daily approval counts with automatic parsing of legacy timestamp formats.
- Websocket endpoints (`/ws/dashboard`, `/ws/logs`) push real-time dashboard and log updates to clients with permission-aware gating.

### 7.4 Log Management
- Log entries persist through SQLAlchemy with worm-guard enforcement on audit tables.
- Alerts/listeners can subscribe to log events in-process; websocket streaming uses the same listener infrastructure.
- Redaction policies scrub sensitive keys (`password`, `token`, `secret`) before persistence.
- CLI utilities hash and verify audit log chains for tamper evidence.

---

## 8. Automation, AI & Recommendations

### 8.1 AI Assistance
- `rewrite_text` and `summarize_text` call OpenAI’s Chat Completions API when keys are configured; otherwise they fall back to deterministic prompt reversal for offline testing.
- Input prompts are compressed to stay within token limits, and validation prevents empty requests.

### 8.2 Workload Balancing
- In-memory worker registry assigns jobs to the least-loaded worker, exposes Prometheus counters for registrations, assignments, and deregistrations, and persists state to disk.
- CLI and API endpoints can load/save worker state to `worker_state.json` (override via `DOCREVIEW360_WORKER_STATE`).

### 8.3 Guardrails & Quality
- Guardrail middleware inspects AI output for PII when enabled, leveraging Nemo Guardrails hooks.
- Approval likelihood scoring and reviewer models provide hooks for future ML-driven prioritisation.

---

## 9. Integrations & Extensibility

### 9.1 Signature Providers
- Documenso integration handles request, status, completion, and webhook flows while respecting the active provider registry.
- Sandbox signature provider enables local development without external callbacks.
- CLI command `verify-signatures` replays verification jobs across approvals with optional parallel execution.

### 9.2 Plugin System
- Global `PluginRegistry` enforces unique names, enable/disable states, and dynamic loading from configured modules.
- `load_plugins` imports modules that expose a `register(registry)` function, letting extensions add editors, automation hooks, or analytics.

### 9.3 External Systems
- Configurable log connectors (type, endpoint, API key, batch size) push audit data to external observability stacks.
- CMS utilities allow pushing TipTap HTML to downstream repositories.
- SharePoint and other integrations (e.g., HR sync, GitHub sync) are scaffolded as optional modules within `integrations/` for future wiring.

### 9.4 Environment Profiles
- Environments are defined in `environments.yaml`; switching updates `DOCREVIEW360_ENV` and returns host metadata for UI theming.
- Missing or malformed YAML raises validation errors to avoid silent misconfiguration.

---

## 10. Platform Surfaces

### 10.1 Backend API
- FastAPI application with CORS/GZip middleware, Markdown rendering, OAuth2 password flow support, and dependency-based RBAC gates.
- REST endpoints cover documents, projects, workflows, approvals, templates, watchlists, dashboard visibility, analytics, archives, comments, AI helpers, CMS pushes, environment switching, and plugin management.
- Websocket routes stream dashboard metrics, operational logs, and collaborative editing payloads.
- API responses leverage Pydantic models with aliasing to match frontend expectations.

### 10.2 Frontend (Next.js)
- Auth-guarded dashboard renders KPI cards, pie/line charts, activity timelines, and log tables with filtering.
- Pages exist for project lists, document viewers, workflow designers, integrations, configuration panels, login/signup, and help content.
- `authenticatedFetch` utility injects auth headers while gracefully handling offline states.
- Component library uses Tailwind + Radix primitives; charts rely on Recharts with theme-aware palettes.

### 10.3 CLI
- `docreview360 init` interactive wizard writes `docreview360.yaml`, chooses database/editor/auth/CMS backends, and optionally seeds sample content.
- `docreview360 migrate export|import` moves persisted data between environments.
- `docreview360 rbac-admin` manages role-to-permission mappings and syncs them to settings.
- `docreview360 logs hash-chain|verify-chain` builds and verifies tamper-evident log chains.
- `docreview360 verify-signatures` revalidates digital signatures across approvals with optional parallel execution.

### 10.4 Background Tasks & Services
- Celery workers run scheduled reminder/escalation jobs and integrity verification tasks.
- Monitoring counters (`monitoring.py`, Prometheus metrics) track approval retries, verification durations, and balancer activity.
- Flower integration script is included for local task inspection.

### 10.5 Persistence & Storage
- Default SQLite databases power projects, RBAC roles, logs, and search state; URLs can be overridden for Postgres/MySQL.
- Documents persist in-memory for the prototype but maintain SHA-256 hashes and revision IDs to support future external storage.
- Object storage helpers abstract uploads for archives and exported artefacts.
- Backup utilities support exports/imports with bagging hooks.

---

## 11. Security, Compliance & Auditability

1. **RBAC Enforcement** – `require_role`/`require_permission` dependencies secure endpoints, and helper APIs expose role maps for UI configuration.
2. **Audit Logging** – Every significant action writes append-only JSON lines with optional HMAC signatures, on-disk anchors, and hash-chain verification.
3. **Log Governance** – WORM guard prevents deletes/updates on audit tables; purge routines respect retention settings and call `should_purge` policies.
4. **Signature Integrity** – Verification jobs download certificates, update provider health, and escalate anomalies. Fallback flags allow controlled bypasses in offline environments.
5. **Data Hygiene** – Document and comment pipelines sanitise HTML, strip scripts, and normalise newline handling to avoid injection vectors.
6. **Secret Management** – Secrets flow through `secrets.py` with optional vault configuration; environment loader reads `.env` for local runs.
7. **Monitoring & Alerts** – Prometheus counters and log alert hooks enable external monitoring or on-call automation.

---

## 12. Operational Expectations

- **Deployment Targets** – Containerised via Docker (FastAPI + Uvicorn + Celery) with docker-compose wiring for frontend, backend, and worker services.
- **Configuration** – `docreview360.yaml`, `settings.yaml`, environment variables, and provider registries govern behaviour; updates propagate through REST endpoints and CLI commands.
- **CORS & Auth** – CORS origins configurable via environment variable. OAuth2 password flow exposes token endpoints; cookies + CSRF header supported for browser clients.
- **Health & Status** – `/health`, `/status/public`, and `/status/internal` endpoints expose readiness and high-level metrics; admin dashboard combines summary stats with system status checks.
- **Testing & Tooling** – Ruff, pytest, and mypy form the default quality gates. Optional mkdocs build supports documentation updates.
- **Extensibility** – Plugins, provider entry points, and stub modules serve as scaffolding for future integrations (e.g., SharePoint, Okta, GitHub).

---

## 13. Success Metrics & KPIs

1. **Document throughput** – Measure drafts completed per week via throughput dashboards and CSV exports.
2. **Approval latency** – Track time from assignment to signature using approval timestamps and Celery reminder logs.
3. **User engagement** – Monitor active projects per user, comment volume, and watchlist counts.
4. **System integrity** – Verify audit hash chains nightly and monitor signature verification counters for anomalies.

---

## 14. Open Questions & Future Considerations

- Align document storage with external object stores to persist binary artefacts beyond in-memory prototype constraints.
- Finalise CMS connectors (SharePoint, Confluence, GDrive) to move from stubs to production-ready sync jobs.
- Expand AI workload balancing into automatic writer assignment from the worker state registry.
- Harden collaborative editing by bundling `y_py` and providing reconnect/recovery UX in the frontend.
- Integrate configurable notification delivery (email, Teams, Slack) with the existing message template catalogue.

