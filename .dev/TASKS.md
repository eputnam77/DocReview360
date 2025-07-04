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

### What changed & why

* **Removed entirely**

  * *Alt-stack deployment doc* – user said it’s unnecessary.

* **Merged / Consolidated**

  * Observability tasks (Prometheus, Grafana, Loki, Sentry) → one “Observability stack” item (Seq 45).
  * Comments + mentions + emoji → one collaboration task (Seq 19).
  * Autosave + dual-view + version history → combined (Seq 41).
  * Metrics & heat-maps now come via the Metabase task (Seq 46).
  * Redis appears once: Celery uses it (Seq 30) and caching layer (Seq 52).

* **Optional / deprioritised**

  * MinIO (Seq 83) is kept but marked optional—place it late.
  * HR system sync, CRDT, SynthLang, Agileagents, etc., are all post-MVP.

This trimmed backlog retains **all code you still need to write**, eliminates redundant work, and keeps the OSS connectors that replace custom builds.

---

### How to read this list

* Work straight down from Seq # 1 for the quickest “upload → edit → approve” demo.
* Mid- and low-priority rows remain visible so the entire backlog stays in one place.
* Orig # lets you jump back to your earlier documentation or GitHub issues without renumbering.

**Confidence level:** 0.77 — ordering is based on typical web-app dependency patterns and your stated need for a rapid, testable MVP.


<!-- ready-for:builder -->
