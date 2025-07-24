**DocReview360 — Consolidated Product Requirements Document (PRD)**
*(v 2025-07-04 — unified, de-duplicated, and aligned with best-in-class open-source tooling)*

---

## 0. Alternative “Turn-Key” Stack

Before installing DocReview360 from source, agencies that prefer a largely pre-integrated suite can deploy **Alfresco Community (ECM) + ONLYOFFICE Docs Community (browser editors) + Camunda (BPMN engine) + Documenso (signatures)** in FedRAMP-eligible containers.
This bundle already covers content storage, collaborative editing, process orchestration, and legally binding e-signatures, and DocReview360 can interact with it through its REST/GraphQL gateway. ([docs.alfresco.com][1], [onlyoffice.com][2], [camunda.com][3], [documenso.com][4])

---

## 1. Executive Summary

DocReview360 is an open-source, web-first platform for drafting, reviewing, approving, publishing, and archiving complex documents (e.g., FAA ACs, policies, manuals). It combines:

| Pillar                 | Primary OSS Component(s)                                     | Purpose                          |
| ---------------------- | ------------------------------------------------------------ | -------------------------------- |
| **Editing**            | TipTap (default), Toast UI Editor, ONLYOFFICE Docs connector | Rich-text / WYSIWYG / XML / DOCX |
| **Workflow**           | Camunda or Imixs-Workflow                                    | BPMN-driven, stateful reviews    |
| **Signatures**         | Documenso                                                    | Secure e-sign & audit trail      |
| **Search & Analytics** | OpenSearch + Metabase                                        | Full-text & BI dashboards        |
| **AuthN/AuthZ**        | Keycloak                                                     | SSO, MFA, RBAC                   |
| **UI Framework**       | React 18 + Next.js 14 & React Flow (admin only)              | Modern, node-based UX            |

Each module is hot-swappable via a plugin contract, ensuring future tooling can be added without core rewrites.

*Business objectives & success metrics* remain unchanged (50 % faster creation, 75 % faster reviews, etc.).

---

## 2. User Roles

| Role                | Key Privileges                                         |
| ------------------- | ------------------------------------------------------ |
| **Admin**           | Configure auth, editors, templates, workflows, plugins |
| **Project Manager** | Create projects, set phases, assign reviewers          |
| **Author/Editor**   | Draft, import, convert, respond to comments            |
| **Reviewer/SME**    | Inline comments, change-tracking, sign/approve         |
| **Viewer**          | Read-only, download exports, view audit logs           |

---

## 3. Functional Requirements

### 3.1 Document & Template Management

* **Custom document types / categories** with import-export.
* **Template engine**: Markdown, TipTap JSON, DOCX, XML.
* **Type conversion wizard** (e.g., AC → Policy) preserving numbering & metadata.
* **Template & Doc-Type Manager UI** for uploading golden Markdown templates, editing in Monaco, and generating derivatives. Accessible via **Configuration → Templates**. All editor templates are persisted in the database for versioning.
* **Multi-format templates**: administrators may create templates in JSON, HTML, or DOCX and input the raw text or upload a file through the UI. These templates are stored in the DB rather than on disk.
* **Per-document linter & numbering toggles** with one-click migration to the latest template version.
* **Project form includes Phase & Workflow fields** with defaults mapped from document type.
* **Document types can link to a default content template**. When a project is created using that type, the associated template is automatically loaded into the editor the first time the document is opened.
* **Message templates** for review requests, approvals and rejections. Templates store text used by email or chat notifications with placeholders for `{project_link}`, `{user}` and `{comments}`. All message/email templates are saved in the database.
* **Project Lead field** replaces “Subject Matter Expert”. It defaults to the logged-in user on project creation but can be changed before saving.

### 3.2 Editors

1. **TipTap** — headless ProseMirror framework, extensible via extensions. ([github.com][5])
2. **Toast UI Editor** — dual Markdown/WYSIWYG modes. ([github.com][6])
3. **ONLYOFFICE Docs** connector for full DOCX fidelity. ([onlyoffice.com][2])
4. **XML block editor** (Monaco-based) for strictly structured specs.

* Real-time autosave, dual-view (rich & source), Pandiff diffing, TipTap change bars.

### 3.3 Workflow & Approvals

* **BPMN templates** editable by admins in a React Flow canvas; end-users see a Wrangle-style linear checklist. ([reactflow.dev][7])
* **Camunda** as default engine; **Imixs-Workflow** supported for lighter installs. ([camunda.com][3], [imixs.org][8])
* Dynamic reviewer add/remove within configured guard-rails.
* **Workflow Designer UI** lets project managers clone BPMN templates and adjust SLAs per project.
* **Documenso approval button** exposes e-signature steps directly in project pages.
* **Documenso** signatures bound to workflow state; cryptographically verified. ([documenso.com][4])
* **Editable approval comments** so reviewers can update their remarks after signing.
* **Automatic notification** to the document owner when reviewers add or update approval comments.
* **Confirmation pop-ups** appear before a user resets their approval or removes a reviewer from the approvals list.
* **Project leads and technical writers can send documents for review and respond to comments.**

### 3.4 Collaboration

* Inline comments, threads, mentions, emoji reactions.
* Concurrent editing with conflict-resolution.
* AI helpers (Prompt-Engine, SynthLang, ruv-FANN anomaly alerts).
* **Project Watchlist** lets any user star a project to follow its progress.

### 3.5 Search, Dashboards & Logs

* **OpenSearch** cluster for full-text & vector queries. ([opensearch.org][9])
* **Metabase** for ad-hoc BI and KPI dashboards. ([metabase.com][10])
* Structured, ISO-8601 logs (INFO-ERROR-CRITICAL) exposed via Grafana Loki or OpenSearch Dashboards.
* Interactive dashboards with project filters and export options.
* Sortable project tracker table linking to per-project details.
* **Document types in progress** widget shows counts of active projects per type.
* Saved search queries and real-time log viewer.

### 3.6 Export & Archival

* One-click multi-format export: PDF, DOCX, HTML, Markdown, XML.
* Archive tiers: TipTap JSON (source) → Markdown (portable) → PDF (immutable).
* GitHub integration to push/pull documents for versioned review and long-term archival.
* NeMo-Guardrails middleware for PII/style conformance before publish.

### 3.7 Security & Compliance

* **Keycloak** OIDC/SAML with MFA. ([keycloak.org][11])
* **Login.gov** SAML broker for federal SSO. ([login.gov][12])
* **Okta** SSO option for commercial orgs. ([okta.com][13])
* **HID Global PIV/CAC** smartcard login. ([hidglobal.com][14])
* **Auth0** OIDC provider for SaaS deployments. ([auth0.com][15])
* RBAC down to field-level; CSP, CSRF, JWT rotation.
* FedRAMP Moderate controls mapped; daily encrypted backups.
### 3.8 Setup & Administration

* **First-run setup wizard** guides initial DB, auth, storage and editor configuration.
* **Core settings locked after onboarding**: chosen database engine and authentication provider become read-only once the wizard completes. Admins must spin up a new instance and migrate if they need to switch.
* **Global Settings** panel with tabs for general, auth, storage, email, plugins and backup. Core values show a “Reinitialize to change” tooltip linking to migration docs.
* **Plugin Marketplace** installs discoverable packages from PyPI in one click.
* **Backup/Restore panel** triggers Celery tasks and monitors progress.
* **Environment switcher** toggles dev/stage/prod endpoints with color cues.
* **RBAC role editor** exposes a permission matrix per role.
* **Scheduled task cron editor** manages Celery Beat schedules.
* **Downloadable CLI profile** lets users fetch `docreview360.env` from the UI.
* **Admin-less project creation wizard** for non-admin authors.
* **Phases configuration page** allows admins to manage workflow phases.
* **Document numbering options** let admins choose sequential numbering or manual entry per project. Document IDs remain 32-character hex strings (e.g., "AC 20.11", "PS-20.1191").
* **Integrations settings page** redesigned for easier configuration via `/config`.
* **In-app docs page** reachable from the Support menu.
* **Migration CLI (`docreview360 migrate`)** exports data from one instance and imports it into another, enabling safe reinitialisation when switching DB or auth backends.

#### Configuration Change Decision Framework

| Question | If “Yes” → Re-initialize | If “No” → Safe to toggle |
| --- | --- | --- |
| Does the change alter the **data store or schema**? | ✔ (DB engine, new auth schemas) | ✖ |
| Could it **invalidate existing data** or require bulk migration? | ✔ | ✖ |
| Does it alter the **security posture**? | Often ✔ | Possibly ✖ if minor |
| Is it a **presentation or feature flag**? | ✖ | ✔ |
| Is rollback **trivial** and state-free? | ✖ | ✔ |

### 3.9 AI Chat Bot

* **Conversational assistant** accessible from the dashboard.
* Queries the project database (projects, assignments, workflow state) to answer
  questions like “who is assigned to X project?” or “what’s the status of X?”.
* Pluggable retrieval pipeline for additional knowledge sources (e.g., docs,
  support tickets).

---

## 4. Technical Architecture

### 4.1 Backend (Python 3.12)

* FastAPI, SQLAlchemy, Pydantic v2.
* PostgreSQL + pgvector, Redis, MinIO/S3.
* Celery workers; WebSockets via FastAPI-WebSocket.

### 4.2 Frontend

* Next.js 14, TypeScript 5, TailwindCSS & shadcn/ui.
* React Query & Zustand for state.
* Editor bundles loaded on demand.

### 4.3 DevOps

* Docker-compose (dev) → Helm charts (prod, EKS/AKS).
* GitHub Actions CI, Terraform IaC, Trivy image scanning.
* In-browser Terraform plan viewer with OPA policy checks.

---

## 5. Plugin & Extension Model

```text
plugins/
 ├─ editors/
 │   └─ tiptap_docx_export.py
 ├─ workflow/
 │   └─ camunda_adapter.py
 ├─ auth/
 │   └─ keycloak_provider.py
 └─ ai/
     └─ ruv_fann_lint.py
```

Each plugin registers entry points (`setup.py`) so integrators can ship new editors, exporters, AI linters, or auth back-ends without touching core.

---

## 6. UI & UX Principles

* **Admin pages** expose React Flow modeller; **users never see nodes/edges** — they interact with step cards and progress bars.
* Everything is keyboard accessible (WCAG 2.1 AA).
* Dark-mode & reduced-motion preferences respected.

---

## 7. Development Roadmap (key delta vs. original)

| Q       | Major Deliverable                                           |
| ------- | ----------------------------------------------------------- |
| Q3 2025 | Core CRUD, TipTap, Keycloak, OpenSearch, basic Camunda flow |
| Q4 2025 | Documenso integration, multi-editor support, AI helpers     |
| Q1 2026 | Export/Archival pipeline, interactive dashboards, setup wizard and admin panels |
| Q2 2026 | Plugin marketplace, environment switcher, RBAC editor, multi-tenant SaaS |

---

## 8. Risks & Mitigations (updates)

| Risk                       | Mitigation                                                            |
| -------------------------- | --------------------------------------------------------------------- |
| OSS project abandonment    | All third-party libs containerised; forks maintained in DocReview360-org. |
| Heavy BPMN engine overhead | Offer Imixs or built-in lightweight JSON state-machine.               |
| Keycloak complexity        | Provide turnkey Helm chart with defaults & scripted realm import.     |

---

## 9. Future-Proofing

* **GraphQL read layer** planned for 2026 to simplify ad-hoc integrations.
* **Web-native CRDT** research for offline editing sync.
* Optional migration path to **OpenSearch Serverless** when FedRAMP-High certified.

---

## 10. Quality & Testing Requirements

Full end-to-end (E2E) tests must verify the entire user journey—from the
`docreview360` CLI commands that bootstrap a project to the browser-based
workflows. The Playwright suite spins up the FastAPI server, drives a real
browser and exercises background services. The CI pipeline installs the
Playwright browsers and runs `pytest -m e2e` in headless mode so regressions are
caught before release.

---

### References

TipTap editor ([github.com][5]) Toast UI Editor ([github.com][6]) Documenso ([documenso.com][4]) Camunda ([camunda.com][3]) Imixs-Workflow ([imixs.org][8]) Metabase ([metabase.com][10]) Keycloak ([keycloak.org][11]) Login.gov ([login.gov][12]) Okta ([okta.com][13]) HID Global ([hidglobal.com][14]) Auth0 ([auth0.com][15]) OpenSearch ([opensearch.org][9]) Alfresco Community ([docs.alfresco.com][1]) ONLYOFFICE Docs ([onlyoffice.com][2]) React Flow ([reactflow.dev][7])
