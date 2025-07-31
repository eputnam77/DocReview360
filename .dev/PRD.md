**DocReview360 — Consolidated Product Requirements Document (PRD)**

*(v July 3, 2025 — unified, de-duplicated, and aligned with best-in-class open-source tooling)*

---

DocReview360 is an open-source, web-first platform for drafting, reviewing, approving, publishing, and archiving complex documents (e.g., FAA ACs, policies, manuals). It combines:

| Pillar                 | Primary OSS Component(s)                                     | Purpose                          |
| ---------------------- | ------------------------------------------------------------ | -------------------------------- |
| **Editing**            | TipTap, Office Online embed for MS Word, ONLYOFFICE Docs viewer (default) | Rich-text / DOCX |
| **Workflow**           | Built-in JSON workflows | Simple state-machine reviews |
| **Signatures**         | Documenso | Secure e-sign & audit trail      |
| **Search & Analytics** | OpenSearch + Metabase | Full-text & business intelligence dashboards        |
| **AuthN/AuthZ**        | Keycloak                                                     | SSO, MFA, RBAC                   |
| **UI Framework**       | React 18 + Next.js 14 (admin only)              | Modern, node-based UX            |

Each module is hot-swappable via a plugin contract, ensuring future tooling can be added without core rewrites.

*Business objectives & success metrics* remain unchanged (50 % faster creation, 75 % faster reviews, etc.).

---

## 2. User Roles (Default)

The following table reflects the system’s **baseline role‑based access configuration**. These settings are applied automatically when a new project or workspace is created. An Administrator may adjust, extend, or revoke any role or permission at any time to meet program‑specific or agency‑specific requirements.

| Permission / Action                | **Admin** | **Editor** | **SME** | **Reviewer** | **Project Mgr** | **Manager** | **Observer**  |
| ---------------------------------- | :-------: | :--------: | :-----: | :----------: | :-------------: | :---------: | :-----------: |
| View dashboards & projects         |    ✔    |    ✔    |    ✔    |    ✔    |    ✔    |    ✔    |    ✔    |
| Create projects                    |    ✔    |    ✔    |    ✔    |    —    |    ✔ (metadata only)    |    —    |    —    |
| Configure auth, templates, plugins |    ✔    |    —    |    —    |    —    |    —    |    —    |    —    |
| Draft / edit documents in the UI   |    ✔    |    ✔    |    ✔    |    —    |    —    |    —    |    —    |
| Download / upload Word documents   |    ✔    |    ✔    |    ✔    |    ✔    |    ✔    |    ✔    |    —    |
| Delete Word or TipTap documents    |    ✔    |    —    |    —    |    —    |    —    |    —    |    —    |
| Lock / publish a draft             |    ✔    |    ✔    |    ✔    |    —    |    —    |    —    |    —    |
| Assign / remove reviewers          |    ✔    |    ✔    |    ✔    |    —    |    ✔    |    —    |    —    |
| Add project status comments        |    ✔    |    ✔    |    ✔    |    —    |    ✔    |    —    |    —    |
| Approve / sign documents           |    —    |    ✔ (own docs only)    |  ✔ (own docs only)  |    ✔ (own docs only)    |    —    |    ✔ (own docs only)    |    —    |
| Add comments to project comments table |    ✔    |    ✔    |    ✔    |    ✔    |    —    |    ✔    |    ✔    |
| Delete projects                   |    ✔    |     —    |    —    |    —    |    —     |    —    |    —     |

Clarification
* Admin — May delete projects or documents, but should do so only in exceptional cases; most Federal records must be retained.
* SME (Project Lead) — Owns the project, often creates it, and drafts the initial version. Signs only for projects where they are designated SME; otherwise acts as a Reviewer.
* Reviewer — Non‑manager who can comment on and formally approve documents (e.g., attorneys, policy analysts, SMEs on other projects).
* Project Manager — Creates placeholder projects; SMEs or Editors fill in the details.
* Observer — Read‑only access; no active responsibilities within a project.

---

## 3. Functional Requirements

### 3.1 Document & Template Management

* **Custom document types / categories** with import-export.
* **Template engine**: TipTap JSON, DOCX.
* **Type conversion wizard** (e.g., AC → Policy) preserving numbering & metadata.
* **Template & Doc-Type Manager UI** for uploading golden templates and generating derivatives. Accessible via **Configuration → Templates**. All editor templates are persisted in the database for versioning.
* **Multi-format templates**: administrators may create templates in JSON, HTML, or DOCX and input the raw text or upload a file through the UI. These templates are stored in the DB.
* **Per-document linter & numbering toggles** with one-click migration to the latest template version.
* **Project form includes Phase & Workflow fields** with defaults mapped from document type.
* **Document types can link to a default content template**. When a project is created using that type, the associated template is automatically loaded into the editor the first time the document is opened.
* **Message templates** drive email and chat notifications. The system ships with six built‑in email templates – **Review Request**, **Reminder: Review Due Soon**, **Overdue Escalation**, **Approval Confirmation**, **Feedback Provided**, and **Re‑Review Request**. Users may create additional templates and disable any they do not need, but the defaults cannot be removed. Templates support `{project_link}`, `{user}` and `{comments}` placeholders and are persisted in the database.
* **Document Checker** validates uploaded DOCX files for FAA style and accessibility, returning a corrected copy.
* **Special Conditions Doc Builder** launches an external tool for generating legally formatted notices.

#### 3.1.1 DOCX Revision History

* Immutable DocumentVersions table
* Draft-0 template rule
* Revision-history UI panel (+ diff, restore)
* SharePoint toggle behaviour

#### 3.1.2 Storage Strategy (design note)

The following table identifies two viable ways to track every DOCX revision.

| Option                                                  | How it works                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Pros                                                                                                                                                                                    | Cons                                                                                                                                                                                                        |
| ------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **A. In-app “Revision History” table**                  | • Every time a user uploads a DOCX, the backend stores the file under `project/{id}/v{n}.docx` and appends a row to **DocumentVersions** (`version`, `uploaded_by`, `uploaded_at`, `sha256`, `notes`).<br>• Draft 0 is the template delivered when the project is created; first user upload becomes Draft 1, and so on.<br>• UI: a **Revision History** panel (grid or timeline) under the Document tab showing version #, uploader, timestamp, download link, and an optional “Diff” button that runs OpenXmlPowerTools to create a redline against the prior version.                      | • No external dependency.<br>• Works offline and in air-gapped enclaves.<br>• Easy to tag “milestone” versions or restore an old draft.                                                 | • You own storage, backups, retention logic.<br>• Duplicate copies if the agency already uses SharePoint.                                                                                                   |
| **B. SharePoint-native versioning via Microsoft Graph** | • Store the working DOCX in a SharePoint document library.<br>• Enable **major/minor versioning** (Library Settings → Versioning). SharePoint automatically creates `v1.0`, `v2.0`, … every check-in and captures who/when.<br>• Your app surfaces that history by calling `GET /drives/{drive-id}/items/{item-id}/versions` (Graph API) to pull the same metadata and expose it in your UI.<br>• Uploading a new draft is just `PUT /content` to the same driveItem; SharePoint bumps the version and keeps the delta. | • Records stay in the agency’s official repository with built-in retention & legal hold.<br>• No extra blob storage to manage.<br>• Users can co-author in Word for the web if desired. | • Requires SharePoint tenant access + OAuth (Graph) plumbing.<br>• Network latency; impossible in fully disconnected networks.<br>• Major/minor numbering (1.1, 1.2) may not map one-to-one with “Draft 3”. |

##### Recommended path

1. **Default to Option A** inside the tool so every deployment (even air-gapped) has a first-class revision table.
2. **Add a “Connect to SharePoint” toggle** in Admin settings:
   *If enabled*, the app writes/reads via Microsoft Graph **and** still records a shadow row in `DocumentVersions` table pointing to the SP version ID.
   You can migrate later without losing history.

##### Document versions

> ```
> DocumentVersions( id, project_id, version_int,
>                   file_uri, uploaded_by, uploaded_at, sha256 )
> ```
>
> * Draft 0 = generated template
> * On each upload, increment `version_int`, store the file, and append a row.
> * Expose a “Revision History” panel that lists version, uploader, timestamp, and provides:
>   • Download link • “View diff” (redline vs previous) • Restore (privileged).
> *If **SharePoint integration** is enabled, use the library’s native versioning (`driveItem/versions`) as the authoritative source and store its `versionId` in the table.*

### 3.2 Editors

1. **TipTap** — headless ProseMirror framework, extensible via extensions.
2. **Office Online** embed for MS Word documents.
3. **ONLYOFFICE Docs** viewer for full DOCX fidelity.

* Real-time autosave, dual-view (rich & source), Pandiff diffing, TipTap change bars.
* **Every save persists the document to PostgreSQL with a revision entry**, ensuring crashes or restarts do not lose work. A `document_versions` table retains prior content for rollback.
* Custom TipTap extensions provide a slash-command menu, heading locks, indentation controls, draggable section nodes with structure validation, watermark overlays, optional MarkReview markup and Yjs-based collaboration.

### 3.3 Workflow & Approvals

* Dynamic reviewer add/remove within configured guard-rails.
* **Workflow Designer UI** lets project managers clone workflow templates and adjust SLAs per project.
* **Documenso approval button** exposes e-signature steps directly in project pages.
* **Documenso** signatures bound to workflow state; cryptographically verified. ([documenso.com][4])
* **Editable approval comments** so reviewers can update their remarks after signing.
* **Automatic notification** to the document owner when reviewers add or update approval comments.
* **Confirmation pop-ups** appear before a user resets their approval or removes a reviewer from the approvals list.
* **Delegated sign-off** is data-driven: a `Delegations` table stores `principal_id`, `delegate_id`, `scope`, `start_date`, `end_date`, and `proof_uri`. Approval lookups include valid delegates; approvals record `actor_type` and a daily job emails upcoming expirations. If acting, the UI displays “Acting for → Mgr Smith (until 08 Aug 2025)”.
* **Project leads and technical writers can send documents for review and respond to comments.**

### 3.4 Collaboration

* Inline comments, threads, mentions, emoji reactions.
* Concurrent editing with conflict-resolution.
* AI helpers (Prompt-Engine, SynthLang, ruv-FANN anomaly alerts).
* **AI workload balancer** distributes background jobs across workers.
* **Project Watchlist** lets any user star a project to follow its progress.

### 3.5 Search, Dashboards & Logs

* **OpenSearch** cluster for full-text & vector queries.
* **Metabase** for ad-hoc BI and KPI dashboards.
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
* See DOCX versioning in 3.1.1.

#### 3.6.1 Archival Package Format (Configurable)

| Field                   | Specification                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Purpose**             | Define how the system bundles the *final document*, *revision log*, and *approvals list* for long-term record-keeping.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| **Configuration point** | During **workspace initialization** the System Administrator SHALL select **exactly one** package format from the options below. The choice is stored in `workspace.settings.archive_package_type` and is immutable for that workspace.                                                                                                                                                                                                                                                                                                                                                                     |
| **Supported formats**   | 1. **BagIt ZIP**  <br> • Payload folder + `manifest-sha256.txt` per RFC 8493. <br> • `bag-info.txt` includes project ID, record schedule, checksum.  <br><br>2. **METS / PREMIS Submission Information Package (SIP)**  <br> • Root `mets.xml` conforming to METS 1.6 schema. <br> • PREMIS 3.0 events for each fixity check. <br> • Payload files in parallel directory.  <br><br>3. **Microsoft 365 Purview Export Package**  <br> • Applies only when the authoritative DOCX resides in SharePoint Online. <br> • System triggers Purview eDiscovery *Export*, stores returned ZIP plus `ExportKey.txt`. |
| **Runtime behaviour**   | When a project transitions to **PUBLISHED**:  <br>1. Generate the chosen package.  <br>2. Validate fixity (BagIt `bagit.py --validate`; METS `metsValidator`; Purview checksum XML).  <br>3. Upload to the configured records repository.  <br>4. Write an entry to `Archives(doc_id, package_type, sha256, location_uri, timestamp)`.                                                                                                                                                                                                                                                                      |
| **Acceptance criteria** | *AC-1* Administrator can select one of the three formats during workspace setup; UI prevents proceeding without a choice. <br>*AC-2* Publishing a project produces a package of the selected type and logs success. <br>*AC-3* Validation failure blocks archive, flags **ARCHIVE\_FAILED**, and emails Records Manager.                                                                                                                                                                                                                                                                                    |
| **Rationale**           | Allows each FAA / DOT environment to align with its existing records workflow—simple BagIt, rich METS/PREMIS, or native Microsoft 365 export—without code changes.                                                                                                                                                                                                                                                                                                                                                                                                                                          |

* **Automated Records Archiving** — When a final project reaches **PUBLISHED**, the system SHALL automatically:
  1. Flatten the final DOCX and generate PDF/A.
  2. Export the complete Documenso approvals list.
  3. Package all artefacts in a BagIt-compliant ZIP, including checksums.
  4. Upload the package to the agency records repository via REST and log the returned record ID.
  5. Notify the SME and Records team on success, or flag `ARCHIVE_FAILED` with a manual retry option.

### 3.7 Security & Compliance

* **Keycloak** OIDC/SAML with MFA.
* **Login.gov** SAML broker for federal SSO.
* **Okta** SSO option for commercial orgs.
* **HID Global PIV/CAC** smartcard login.
* **Auth0** OIDC provider for SaaS deployments.
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

* Conversational assistant accessible from the dashboard.
* Queries the project database (projects, assignments, workflow state) to answer
  questions like “who is assigned to X project?” or “what’s the status of X?”.
* Pluggable retrieval pipeline for additional knowledge sources (e.g., docs,
  support tickets).

---

## 4. Technical Architecture

### 4.1 Backend (Python 3.12)

* FastAPI, SQLAlchemy, Pydantic v2.
* PostgreSQL + pgvector, Redis, MinIO/S3.
* Documents stored in PostgreSQL as JSONB or bytea blobs with a `document_versions` table for revision history; large binaries may use MinIO with DB references.
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
 ├─ auth/
 │   └─ keycloak_provider.py
 ├─ storage/
 │   └─ minio_backend.py
 └─ ai/
     └─ ruv_fann_lint.py
```

Each plugin registers entry points (`setup.py`) so integrators can ship new editors, exporters, AI linters, or auth back-ends without touching core.

---

## 6. UI & UX Principles

* **Admin pages** include a drag-and-drop workflow designer; users interact with step cards and progress bars.
* Everything is keyboard accessible (WCAG 2.1 AA).
* Dark-mode & reduced-motion preferences respected.

---

## 7. Development Roadmap (key delta vs. original)

| Q       | Major Deliverable                                           |
| ------- | ----------------------------------------------------------- |
| Q1 2025 | Core CRUD, TipTap, Keycloak, OpenSearch, basic workflow engine |
| Q2 2025 | Documenso integration, multi-editor support, AI helpers     |
| Q3 2025 | Export/Archival pipeline, interactive dashboards, setup wizard and admin panels |
| Q4 2025 | Plugin marketplace, environment switcher, RBAC editor, multi-tenant SaaS |

---

## 8. Risks & Mitigations (updates)

| Risk                       | Mitigation                                                            |
| -------------------------- | --------------------------------------------------------------------- |
| OSS project abandonment    | All third-party libs containerised; forks maintained in DocReview360-org. |
| Workflow engine overhead | Use built-in lightweight JSON state-machine. |
| Keycloak complexity        | Provide turnkey Helm chart with defaults & scripted realm import.     |

---

## 9. Future-Proofing

* **GraphQL read layer** now provides basic query support; advanced features remain on the 2026 roadmap.
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
