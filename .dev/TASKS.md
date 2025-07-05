# Task Breakdown

Below is a high level list of tasks derived from **PRD.md**. Each task contains a priority, estimated effort, acceptance criteria, and suggested GitHub labels.

Below is a **de-duplicated, OSS-aware backlog (87 tasks)**.
Everything that was rendered obsolete by the open-source stack (e.g., a separate “Alt-stack deployment doc”) has been **removed or merged**; overlapping items (e.g., Prometheus + Grafana + Loki) are **consolidated**.

*Seq #* = recommended build order toward a “clickable” MVP in ≈ 6 weeks.
*Orig #* = row(s) from the previous 97-item sheet that this task replaces or combines (— = brand-new or renamed).
Estimates are unchanged unless noted.

| Seq # |  Orig # | Task (merged/renamed items in italics)                                                    | Priority | Est. | Key Acceptance Test                  | Labels                      |
| ----: | :-----: | ----------------------------------------------------------------------------------------- | -------- | ---: | ------------------------------------ | --------------------------- |
|     1 |    1    | Architecture ADR & folder layout                                                          | High     |   2d | `tests/test_task01_architecture.py`  | architecture, documentation |
|     2 |    2    | Project skeleton (`pyproject.toml`, CI)                                                   | High     |   1d | `tests/test_task02_project_setup.py` | setup, devops               |
|     3 |    21   | Quality gates (pytest, ruff, mypy, bandit, pre-commit)                                    | High     |   2d | `tests/test_task21.py`               | testing, devops             |
|     4 |    3    | CLI “`docuflow init`” configuration wizard                                                | High     |   3d | `features/task03.feature`            | backend, cli                |
|     5 |    4    | Plugin framework (editors / exporters / validators)                                       | High     |   3d | `property/test_task04_property.py`   | backend, architecture       |
|     6 |    5    | SQLAlchemy models (all core entities)                                                     | High     |   3d | `property/test_task05_property.py`   | backend, database           |
|     7 |    6    | FastAPI skeleton (CRUD placeholders)                                                      | High     |   4d | `features/task06.feature`            | backend, api                |
|     8 |    7    | OAuth/OIDC stub auth                                                                      | High     |   3d | `features/task07.feature`            | backend, security           |
|     9 |    46   | RBAC middleware (users & roles)                                                           | High     |   3d | `features/task46.feature`            | backend, security           |
|    10 |    —    | **Next.js 14 + Tailwind + shadcn/ui boilerplate**                                         | High     |   3d | `features/task92.feature`            | frontend, setup             |
|    11 |    —    | **State mgmt (React Query + Zustand)**                                                    | High     |   2d | `features/task93.feature`            | frontend, state             |
|    12 |    11   | Workflow engine (*phase + reviewers*)                                                     | High     |   4d | `features/task11.feature`            | backend, workflow           |
|    13 |    8    | Document-type & template CRUD                                                             | High     |   4d | `features/task08.feature`            | backend, feature            |
|    14 |    9    | TipTap editor (upload/edit Markdown + DOCX stub)                                          | High     |   5d | `features/task09.feature`            | backend, editor             |
|    15 |    12   | Approval subsystem (sign / decline)                                                       | High     |   4d | `features/task12.feature`            | backend, feature            |
|    16 |    80   | Documenso e-signature connector                                                           | High     |   3d | `features/task80.feature`            | backend, security           |
|    17 |    18   | React pages (login, dashboard, editor)                                                    | Medium   |   5d | `features/task18.feature`            | frontend                    |
|    18 |    19   | Dashboard widgets (assignments, status)                                                   | Medium   |   4d | `features/task19.feature`            | frontend, feature           |
|    19 | 24 + 20 | **Inline comments w/ mentions & emoji**                                                   | High     |   4d | `features/task24.feature`            | frontend, collaboration     |
|    20 |    40   | Docker-compose dev stack                                                                  | Medium   |   2d | `property/test_task40_property.py`   | devops                      |
|    21 |    14   | Structured logging + query API                                                            | High     |   4d | `features/task14.feature`            | backend, logging            |
|    22 |    26   | WebSocket live updates                                                                    | Medium   |   3d | `features/task26.feature`            | backend, api                |
|    23 | 17 + 43 | Archival workflow (*multi-format & naming*)                                               | Medium   |   4d | `features/task17.feature`            | backend, archival           |
|    24 |    10   | Full-text search (Postgres TS)                                                            | Medium   |   4d | `features/task10.feature`            | backend, search             |
|    25 |    82   | OpenSearch + pgvector upgrade                                                             | High     |   4d | `features/task82.feature`            | backend, search             |
|    26 |    16   | Export pipeline (HTML + MD + PDF + DOCX)                                                  | High     |   5d | `features/task16.feature`            | backend, export             |
|    27 |    38   | Export preview & batch export                                                             | Medium   |   3d | `features/task38.feature`            | backend, export             |
|    28 |    13   | Priority management & temp reassignment                                                   | Medium   |   3d | `features/task13.feature`            | backend, feature            |
|    29 |    22   | Document numbering system                                                                 | Medium   |   2d | `features/task22.feature`            | backend, feature            |
|    30 | 32 + 57 | Celery workers + Redis broker                                                             | Medium   |   3d | `property/test_task57_property.py`   | backend, devops             |
|    31 |    47   | Email notifications (template-driven)                                                     | Medium   |   2d | `features/task47.feature`            | backend, feature            |
|    32 |    30   | Plugin management UI (on/off)                                                             | Medium   |   3d | `features/task30.feature`            | frontend, admin             |
|    33 |    15   | Reporting endpoints & CSV export                                                          | Medium   |   3d | `features/task15.feature`            | backend, reporting          |
|    34 |    23   | AI assist (creation + validation)                                                         | Medium   |   4d | `features/task23.feature`            | backend, ai                 |
|    35 |    32   | AI-validated project init (+ reviewers)                                                   | High     |   4d | `features/task32.feature`            | backend, ai                 |
|    36 |    33   | Doc-type conversion wizard                                                                | Medium   |   3d | `features/task33.feature`            | backend, feature            |
|    37 |    37   | Style-guide manager + compliance                                                          | Medium   |   3d | `features/task37.feature`            | backend, editor             |
|    38 |    35   | TipTap DOCX → headings auto-fix                                                           | Medium   |   4d | `features/task35.feature`            | frontend, editor            |
|    39 |    34   | Multi-editor switching (Toast UI / ONLYOFFICE)                                            | Medium   |   4d | `features/task34.feature`            | frontend, editor            |
|    40 |    53   | Pandiff diff & change-bars                                                                | Medium   |   2d | `features/task53.feature`            | backend, editor             |
|    41 | 60 + 62 | Dual view + autosave & version history                                                    | Medium   |   4d | `features/task60.feature`            | frontend, editor            |
|    42 |    61   | MarkReview track-changes workflow                                                         | Medium   |   3d | `features/task61.feature`            | backend, editor             |
|    43 | 76 + 49 | Keycloak SSO with MFA hardening                                                           | High     |   4d | `features/task76.feature`            | backend, security           |
|    44 |    59   | Security compliance (encryption + retention)                                              | Medium   |   3d | `features/task59.feature`            | backend, security           |
|    45 |    —    | **Observability stack (Prometheus + Grafana + Loki + Sentry)** <br>*consolidates 41 + 51* | Medium   |   4d | `property/test_task97_property.py`   | devops, monitoring          |
|    46 | 45 + 83 | Metabase analytics & heat-maps                                                            | Medium   |   4d | `features/task83.feature`            | frontend, dashboard         |
|    47 |    39   | Real-time log dashboard UI                                                                | Medium   |   3d | `features/task39.feature`            | frontend, logging           |
|    48 |    55   | Saved searches & widgets                                                                  | Low      |   3d | `features/task28.feature`            | backend, dashboard          |
|    49 |    44   | AI export-format suggestions                                                              | Low      |   2d | `features/task44.feature`            | backend, ai                 |
|    50 |    48   | Optional grammar-checker plug-in                                                          | Low      |   2d | `features/task48.feature`            | frontend, ai                |
|    51 |    58   | WCAG 2.1 AA audit pass                                                                    | Medium   |   3d | `features/task55.feature`            | frontend, accessibility     |
|    52 |    63   | Redis caching layer (sessions)                                                            | Medium   |   2d | `property/test_task63_property.py`   | backend, devops             |
|    53 |    66   | AI-ranked search + results export                                                         | Medium   |   3d | `features/task66.feature`            | backend, ai, search         |
|    54 |    70   | SynthLang token-reducer                                                                   | Low      |   2d | `features/task70.feature`            | backend, ai                 |
|    55 |    72   | ruv-FANN anomaly linter                                                                   | Medium   |   3d | `features/task72.feature`            | backend, ai                 |
|    56 |    73   | Priority-escalation notifications                                                         | Medium   |   2d | `features/task73.feature`            | backend, automation         |
|    57 |    74   | Manager approval for long reassign.                                                       | Medium   |   2d | `features/task74.feature`            | backend, workflow           |
|    58 |    49   | Re-review trigger on major edits                                                          | Medium   |   3d | `features/task49.feature`            | backend, workflow           |
|    59 |    50   | Dual public / internal status API                                                         | Medium   |   2d | `features/task50.feature`            | backend, logging            |
|    60 |    36   | AI workload balancer                                                                      | Low      |   3d | `features/task36.feature`            | backend, ai                 |
|    61 |    68   | Agileagents (A2) auto-review bots                                                         | Medium   |   3d | `features/task68.feature`            | backend, automation         |
|    62 |    69   | Prompt-Engine feedback templates                                                          | Medium   |   2d | `features/task69.feature`            | backend, ai                 |
|    63 |    78   | Imixs-Workflow adapter                                                                    | Medium   |   2d | `features/task78.feature`            | backend, workflow           |
|    64 |    77   | Camunda connector plugin                                                                  | High     |   3d | `features/task77.feature`            | backend, workflow           |
|    65 |    84   | React-Flow BPMN admin designer                                                            | Medium   |   3d | `features/task84.feature`            | frontend, workflow          |
|    66 |    81   | Alfresco ECM connector                                                                    | Medium   |   3d | `features/task81.feature`            | backend, storage            |
|    67 |    79   | ONLYOFFICE Docs connector                                                                 | Medium   |   3d | `features/task79.feature`            | frontend, editor            |
|    68 |    85   | Dark-mode & reduced-motion prefs                                                          | Low      |   1d | `features/task85.feature`            | frontend, accessibility     |
|    69 |    54   | Backup & disaster-recovery scripts                                                        | Low      |   2d | `property/test_task54_property.py`   | devops, backup              |
|    70 |    58   | Records Keeper archival folders                                                           | Low      |   2d | `features/task58.feature`            | backend, archival           |
|    71 |    64   | HR API temp reassignment sync                                                             | Low      |   3d | `features/task64.feature`            | backend, integration        |
|    72 |    65   | Sample doc-type & template on install                                                     | Low      |   1d | `property/test_task65_property.py`   | backend, setup              |
|    73 |    20   | Developer & user docs (MkDocs)                                                            | Medium   |   3d | `features/task20.feature`            | documentation               |
|    74 |    29   | Import/export doc-type JSON                                                               | Low      |   2d | `features/task29.feature`            | backend, admin              |
|    75 |    51   | Contextual help & tutorials                                                               | Low      |   2d | `features/task51.feature`            | frontend, docs              |
|    76 |    52   | Terraform IaC templates                                                                   | Medium   |   3d | `property/test_task52_property.py`   | devops, infrastructure      |
|    77 |    86   | Trivy image scanning in CI                                                                | Medium   |   1d | `property/test_task86_property.py`   | devops, security            |
|    78 |    71   | LangGraph-Studio flow debugger                                                            | Low      |   2d | `property/test_task71_property.py`   | devops, monitoring          |
|    79 |    75   | Log-pattern alert rules                                                                   | Low      |   2d | `features/task75.feature`            | backend, logging            |
|    80 |    90   | FedRAMP controls + encrypted backup doc                                                   | Medium   |   2d | `property/test_task90_property.py`   | documentation, security     |
|    81 |    87   | Helm chart for prod deploy                                                                | Medium   |   3d | `property/test_task87_property.py`   | devops, infrastructure      |
|    82 |    88   | Read-only GraphQL read layer                                                              | Low      |   3d | `features/task88.feature`            | backend, api                |
|    83 |    94   | MinIO/S3 object storage plug-in (**optional**)                                            | Low      |   2d | `features/task56.feature`            | backend, storage            |
|    84 |    27   | Multi-DB abstraction (PostgreSQL + option)                                                | Medium   |   4d | `property/test_task27_property.py`   | backend, database           |
|    85 |    60   | Web-native CRDT research prototype                                                        | Low      |   3d | `features/task89.feature`            | research, editor            |
|    86 |    93   | Plugin developer guide & API docs                                                         | Low      |   2d | `property/test_task96_property.py`   | documentation               |
|    87 |    67   | NeMo-Guardrails PII/style gate                                                            | High     |   3d | `features/task67.feature`            | backend, security, ai       |

---

## Ruv-FANN

### Practical Ways to Apply **ruv-FANN** inside DocuFlow

| #  | Use-case                                       | What it delivers                                                                                                       | Where it runs                                                          | OSS add-ons                                                                |
| -- | ---------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| 1  | **Offline style-drift & tense-shift detector** | Flags passages that deviate from your FAA/GPO style corpora in < 5 ms per block                                        | TipTap/Toast editor plugin (WASM) **and** Celery “quality-gate” worker | core `ruv-fann` (Rust) export → PyO3 wheel ([github.com][1], [docs.rs][2]) |
| 2  | **Section classifier & readability scorer**    | Auto-labels headings (Reg text §, Background, Definitions…) and gives Flesch/grade-level; drives conditional templates | Backend micro-service                                                  | `ruv-fann` + training set of labeled paragraphs                            |
| 3  | **Predictive review-duration forecasting**     | Learns from past cycles; dashboard shows “ETA 8.4 days ± 1.1” so PMs can rebalance load                                | Analytics service feeding Metabase                                     | `neuro-divergent` (built on ruv-FANN) ([docs.rs][3])                       |
| 4  | **Reviewer auto-match recommender**            | Suggests top SMEs for a new project based on topic vectors & their history                                             | Workflow engine hook (Camunda task listener)                           | ruv-FANN MLP classifier                                                    |
| 5  | **Audit-log anomaly monitor**                  | Real-time flag if approval/vote patterns differ from learned norm (possible coercion / account hijack)                 | SecOps sidecar                                                         | ruv-FANN streaming inference                                               |
| 6  | **Edge / air-gapped AI fallback**              | Full DocuFlow AI suite works when the OpenAI endpoint is blocked (GovCloud, classified nets)                           | On-prem Python wheel or WebGPU build                                   | `ruv-FANN` → WebGPU WASM path ([linkedin.com][4])                          |
| 7  | **Web-first in-editor inference**              | All linting suggestions happen client-side; zero round-trip latency, no PII leaves browser                             | TipTap plugin compiled with `wasm32-webgpu`                            | repo’s `src/webgpu` target ([linkedin.com][4])                             |
| 8  | **Nightly “quality gate” batch job**           | Blocks promotion to next phase if neural quality score < threshold; pushes report to dashboard                         | Celery beat task                                                       | same model weights as #1                                                   |
| 9  | **Template-conformance neural diff**           | Learns legal numbering / heading cadence and inserts missing blocks automatically                                      | Import/conversion pipeline                                             | cascade-correlation nets in ruv-FANN ([docs.rs][2])                        |
| 10 | **Workload & backlog forecasting**             | Uses ruv-swarm + neuro-divergent to predict document inflow and adjust capacity planning                               | Ops dashboard                                                          | `ruv-swarm-ml`, `ruv-swarm-persistence` ([crates.io][5])                   |

---

#### Implementation Task List (ready to drop into your roadmap)

| Order | Task                                                                                      | Owner             | Phase |
| ----- | ----------------------------------------------------------------------------------------- | ----------------- | ----- |
| 1     | **Curate training corpus** (50 k “gold” FAA/GPO-compliant paragraphs + 5 k anomalies)     | Tech Writing team | P1    |
| 2     | **Train & export models** (`cargo run --bin fann-train …`, output `.fann`)                | ML Eng            | P1    |
| 3     | **Build Python wheel** via *maturin* (`--features pyo3,simd`) and publish to private PyPI | ML Eng            | P2    |
| 4     | **TipTap WASM plugin** (`wasm32-webgpu`) delivering `lint()` & `predict()`                | Front-end         | P2    |
| 5     | **Celery quality-gate worker** consuming wheel; posts block-level scores to DB            | Backend           | P2    |
| 6     | **Camunda listener** for reviewer auto-match; calls `/ai/recommend-reviewers` endpoint    | Workflow          | P3    |
| 7     | **Metabase card & API** for review-duration forecast                                      | Data Eng          | P3    |
| 8     | **Security sidecar** streaming audit logs through anomaly model                           | SecOps            | P3    |
| 9     | **CI pipeline**: SIMD, WASM & native builds tested on every PR                            | DevOps            | P2    |
| 10    | **Docs & user training** (“How DocuFlow neural lint works”)                               | Docs              | P3    |

These integrations keep DocuFlow’s AI **fully on-prem, millisecond fast, and license-free**, while leveraging ruv-FANN’s Rust speed and memory safety.

## Misc

Below is an **“add-on task pack”** you can drop straight into DocuFlow’s roadmap.
Each task either (a) closes an integration gap, (b) hardens security/ops, or (c) unlocks a feature the upstream OSS already ships but your PRD hasn’t scheduled yet.

| #                              | OSS Component                                                                                                        | New Task                                                                                        | Outcome / Why it helps |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | ---------------------- |
| **TipTap 2**                   | Build **DOCX-export extension** in `/plugins/editors/tiptap_docx.ts` using ProseMirror’s node schema → `docx4js`     | One-click Word export from the default editor. ([github.com][1])                                |                        |
|                                | Bundle **Hocuspocus** collab backend (Docker sidecar) + auth middleware                                              | Real-time co-authoring without 3rd-party SaaS. ([github.com][1])                                |                        |
| **Toast UI Editor**            | Add **Markdown-to-XML converter plugin** using unified/rehype & your XML template map                                | Lets tech teams draft once and publish to XML spec. ([github.com][2])                           |                        |
| **ONLYOFFICE Docs**            | Ship Helm chart that autos-registers DocumentServer with DocuFlow via WOPI, including SSL & JWT                      | Zero-click Word/Excel/PowerPoint editing for agencies that ban external SaaS. ([github.com][3]) |                        |
|                                | Create Cypress E2E test suite that opens a .docx, edits, saves, re-opens                                             | Guards against silent breakage after upgrades.                                                  |                        |
| **Camunda 8**                  | Maintain **BPMN template library repo** (`/workflows/*.bpmn`) + GitHub Actions that lints with `camunda-modeler-cli` | Keeps process definitions in version control. ([github.com][4])                                 |                        |
|                                | Author DMN table “Reviewer-Selector” → auto-assign SMEs based on keywords                                            | Removes manual reviewer pick step.                                                              |                        |
| **Imixs-Workflow** (fallback)  | Provide Spring-Boot starter + REST façade so small installs can swap Camunda with Imixs by env-var                   | Lightweight option for orgs that find Camunda heavy. ([imixs.org][5])                           |                        |
| **Documenso**                  | Write **status-webhook listener** (`/api/hooks/documenso`) → triggers Camunda “Signed” message                       | Ensures signature state always syncs to workflow. ([documenso.com][6])                          |                        |
|                                | Build **HashiCorp Vault secret engine** for Documenso’s signing keys                                                 | Separation-of-duty & FISMA key management.                                                      |                        |
| **OpenSearch**                 | Create ILM policy + hot/warm architecture Terraform module                                                           | Keeps log/index costs predictable at scale. ([opensearch.org][7])                               |                        |
|                                | Enable **k-NN plugin** & index embeddings from ruv-FANN for semantic search                                          | Natural-language lookup inside DocuFlow.                                                        |                        |
| **Metabase**                   | Seed **Starter Dashboards** pack (JSON) covering KPIs in PRD; attach row-level permissions via `db_role`             | Gives PMs insights on day 1. ([metabase.com][8])                                                |                        |
|                                | Automate nightly “sync db fields” job after Alembic migrations                                                       | Prevents broken fields in cards following schema change.                                        |                        |
| **Keycloak**                   | Scripted **realm import** + MFA policy + Login.gov broker; pack into Helm                                            | Turn-key FedRAMP-ready SSO. ([opensearch.org][7])                                               |                        |
| **React Flow (admin)**         | Build **DSL → JSON compiler** so admins can author simple `yaml` instead of dragging nodes                           | Faster template authoring; keeps flows in Git.                                                  |                        |
| **Renovate / Dependabot**      | Add **monorepo-wide OSS upgrade bot** with “security-first” schedule                                                 | Auto-PRs for CVE patches on every upstream tool.                                                |                        |
| **Trivy / Grype**              | Extend CI to run container and dependency scans; block merge on HIGH/CRITICAL                                        | Maintains ATO posture across all OSS.                                                           |                        |
| **k6 / Playwright perf tests** | Capture baseline editor latency (TipTap, ONLYOFFICE) before launch                                                   | Detects regressions after each release branch.                                                  |                        |

---

### Scheduling Hints (drop-in to existing phases)

| Phase                    | Add-on items                                                                          |
| ------------------------ | ------------------------------------------------------------------------------------- |
| **P 1 – Prototype**      | Camunda template repo, Keycloak realm import, OpenSearch ILM module                   |
| **P 2 – Core**           | TipTap DOCX export, Hocuspocus collab, Documenso webhooks, Cypress E2E                |
| **P 3 – Advanced**       | Toast UI XML plugin, Reviewer-Selector DMN, k-NN semantic search, Metabase dashboards |
| **P 4 – Prod Hardening** | Vault key engine, Renovate/Trivy pipelines, k6/Playwright baselines                   |

Implementing these extra tasks turns each upstream OSS tool from *“bolted-on”* to *“first-class citizen”* inside DocuFlow—covering author experience, process automation, security, and long-term maintainability.

## Templates

### **Template-Lifecycle Add-On Tasks**

| #        | Task                                                                                                                                                                       | What it achieves                                                         | Owner          | Phase |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ | -------------- | ----- |
| **T-1**  | **Author “Golden Source” Markdown template** for each document type (AC, Policy, Manual, etc.). Store in `templates/md/` with Hugo-style front-matter.                     | Single canonical template that downstream formats inherit from.          | Tech Writing   | P 1   |
| **T-2**  | **Generate TipTap JSON, Toast-MD, XML, and DOCX derivatives** from the Markdown source via a **Pandoc + lua-filter** pipeline; commit to `templates/dist/`.                | Guarantees all editors share identical heading hierarchy & boiler-plate. | DevOps         | P 1   |
| **T-3**  | **Create Jest/Playwright snapshot tests** that open each template in TipTap and Toast UI, then assert: heading count, required blocks present, placeholder text untouched. | Prevents accidental template drift after edits.                          | Front-end      | P 2   |
| **T-4**  | **Write XML Schematron rules** for every template (§, Appendix, Tables) and add an **xmllint GitHub Action** that fails on invalid structure.                              | Validates the XML derivatives before release.                            | Backend        | P 2   |
| **T-5**  | **Build “Template Linter” TipTap plugin** that, on save, compares live doc blocks to the Golden Source AST and highlights missing or extra nodes.                          | Real-time author feedback; zero round-trip to server.                    | Front-end      | P 3   |
| **T-6**  | **Cross-format round-trip test**: Markdown → TipTap → DOCX → Markdown; diff expected vs. actual in CI (`git diff --no-index`).                                             | Ensures converters are lossless and reversible.                          | QA             | P 3   |
| **T-7**  | **Template Version Registry API** (`/api/v1/templates`) with semantic versioning, changelog, and “required upgrade” flag.                                                  | Allows projects to lock or migrate templates safely.                     | Backend        | P 3   |
| **T-8**  | **Admin UI “Diff & Migrate” wizard** that shows visual diff between a doc’s current template and the newest version, with one-click apply.                                 | Smooth transition when a template evolves.                               | UX / Front-end | P 4   |
| **T-9**  | **Sample Content Seeds**: auto-generate one sample file per template & format on install (`docuflow init --seed`).                                                         | Lets users test the whole workflow instantly.                            | Docs           | P 4   |
| **T-10** | **Weekly Renovate bot for templates**: opens PR if upstream Golden Source changes, triggers full conversion & test matrix.                                                 | CI keeps every derivative template fresh.                                | DevOps         | P 4   |

> **Why you need separate test templates?**
> • Editors store structure differently (TipTap JSON vs. Markdown AST vs. Word XML).
> • Snapshot & schema tests catch silent formatting regressions before they hit reviewers.
> • Golden-Source–first workflow guarantees consistent numbering, headings, and boiler-plate across every export path.

Add these tasks to the roadmap to make template maintenance **repeatable, testable, and editor-agnostic**.

## TipTap Plugin Wrappers

Below is a **ready-to-paste “Wrapper Work-Pack”** that adds DocuFlow glue-code for three external TipTap extensions:

* **@your-org/tiptap-template-linter** (the new linter you’ll publish)
* **@your-org/tiptap-markreview** (existing change-tracking plugin)
* **@your-org/tiptap-fed-numbering** (new federal heading/paragraph numbering plugin)

---

## 1. Folder & naming convention

```
docuflow/
└─ plugins/
   └─ editors/
      ├─ tiptap_template_linter_wrapper.ts
      ├─ tiptap_markreview_wrapper.ts
      └─ tiptap_fed_numbering_wrapper.ts
```

Each wrapper exposes a **single default function**:

```ts
export async function register(editor: Editor, ctx: DocuFlowCtx): Promise<void>
```

*`DocuFlowCtx` gives access to JWT, REST client, RBAC, toast bus, etc.*

---

## 2. Wrapper skeletons

### 2.1 Template-Linter wrapper (`tiptap_template_linter_wrapper.ts`)

```ts
import { TemplateLinter } from '@your-org/tiptap-template-linter';
import { fetchGoldenTemplate } from '@/services/templates';

export async function register(editor, ctx) {
  const tplAst = await fetchGoldenTemplate(ctx.docTypeId);

  editor.registerPlugin(
    TemplateLinter.configure({
      templateAst: tplAst,
      onViolation: (violations) => {
        ctx.bus.emit('lint:update', violations);
        if (violations.critical.length) ctx.blockSave('Template violations');
      },
    })
  );
}
```

### 2.2 MarkReview wrapper (`tiptap_markreview_wrapper.ts`)

```ts
import { MarkReview } from '@your-org/tiptap-markreview';

export async function register(editor, ctx) {
  editor.registerPlugin(
    MarkReview.configure({
      userId: ctx.user.id,
      changeBarColor: ctx.theme.accent,
      onExport: (delta) => ctx.api.saveDelta(delta),
    })
  );
}
```

### 2.3 Federal-Numbering wrapper (`tiptap_fed_numbering_wrapper.ts`)

```ts
import { FedNumbering } from '@your-org/tiptap-fed-numbering';

export async function register(editor, ctx) {
  editor.registerPlugin(
    FedNumbering.configure({
      docType: ctx.docTypeCode,           // e.g. 'AC', 'TSO'
      levelMap: ctx.settings.levelMap,    // pulled from org settings
      autoFix: true,
      onRenumber: (map) => ctx.api.saveNumberMap(map),
    })
  );
}
```

---

## 3. Loader hook (one line per wrapper)

```ts
// docuflow/client/editorLoader.ts
import { register as loadLinter }       from '@/plugins/editors/tiptap_template_linter_wrapper';
import { register as loadMarkReview }   from '@/plugins/editors/tiptap_markreview_wrapper';
import { register as loadFedNumbering } from '@/plugins/editors/tiptap_fed_numbering_wrapper';

export async function initEditor(ctx) {
  const editor = createTipTapInstance(ctx.initialContent);

  await Promise.all([
    loadLinter(editor, ctx),
    loadMarkReview(editor, ctx),
    loadFedNumbering(editor, ctx),
  ]);

  return editor;
}
```

---

## 4. Task list (drop into roadmap)

| ID      | Description                                                                | Owner | Sprint |
| ------- | -------------------------------------------------------------------------- | ----- | ------ |
| **W-1** | Scaffold wrappers folder & ctx typings                                     | FE    | S-7    |
| **W-2** | Implement **Template-Linter** wrapper & save-block hook                    | FE    | S-7    |
| **W-3** | Implement **MarkReview** wrapper; wire delta export                        | FE    | S-8    |
| **W-4** | Implement **Fed-Numbering** wrapper; connect org settings API              | FE    | S-8    |
| **W-5** | Add **editorLoader** init that awaits all wrappers                         | FE    | S-8    |
| **W-6** | Cypress tests: open template, trigger linter & numbering, assert UI badges | QA    | S-9    |
| **W-7** | RBAC check: only Editors/Admins can toggle numbering auto-fix              | BE    | S-9    |
| **W-8** | Docs page “Integrating third-party TipTap plugins”                         | Docs  | S-10   |

---

### Why wrappers (vs. baking into the extension)?

* **Separation of concerns** – the extension stays editor-agnostic; the wrapper handles DocuFlow specifics (auth, APIs, theming, RBAC).
* **Upgrade safety** – if TipTap or DocuFlow churn, you touch the wrapper, not the shared package.
* **Multi-tenant config** – wrappers pull tenant-level settings (e.g., numbering map) at runtime.




<!-- ready-for:verifier -->
