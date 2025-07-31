# Traceability Matrix

| Requirement | Task ID | Code Reference | Test Reference |
|-------------|---------|----------------|----------------|
| CLI wizard generates config | Task 4 | `src/docreview360/cli.py` | `tests/test_cli.py` |
| Plugin framework for extensible editors | Task 5 | `src/docreview360/plugins.py` | `tests/test_task05.py` |
| Document types & Template CRUD | Task 13 | `src/docreview360/doc_types.py` | `tests/test_documents.py` |
| TipTap editor MVP | Task 14 | `src/docreview360/tiptap.py` | `tests/test_tiptap.py` |
| Approval subsystem | Task 15 | `src/docreview360/approvals.py` | `tests/test_approvals.py` |
| Project Watchlist feature | Task 115 | `src/docreview360/watchlist.py` | `tests/test_watchlist.py` |
| AI workload balancer | Task 60 | `src/docreview360/ai_balancer.py` | `tests/test_task36.py` |
| Structured log viewer | Task 21 | `src/docreview360/logs.py` | `tests/test_logs_page.py` |
| Configurable file-naming policy | Task 135 | | |
| Document Checker (FAA style) | Task 136 | `src/docreview360/ext/faa_docchecker.py` | `tests/test_ext_docchecker.py` |
| Special Conditions Doc Builder | Task 137 | `src/docreview360/ext/sc_builder.py` | `tests/test_ext_sc_builder.py` |
| Document types in progress widget | Task 138 | | |
| Sortable project tracker table | Task 139 | | |
| First-run setup wizard | Task 140 | | |
| AI chat bot assistant | Task 141 | | |
| Terraform plan viewer with OPA | Task 142 | | |
| Archival package format selector | Task 143 | | |
| User roles & permissions matrix | Task 144 | | |
| Template Manager UI | Task 145 | | |
| Multi-format templates stored in DB | Task 146 | | |
| Linter & numbering per-document toggles | Task 147 | | |
| Default template linkage | Task 148 | | |
| Notification message templates | Task 149 | | |
| Revision history & restore panel | Task 150 | | |
| SharePoint versioning toggle | Task 151 | | |
| TipTap extension pack with collaboration | Task 152 | | |
| Workflow Designer UI | Task 153 | | |
| Documenso approval button | Task 154 | | |
| Dynamic reviewer management | Task 155 | | |
| Comment threads & emoji reactions | Task 156 | | |
| Special Condition (SC)-Intake schema & storage              | 160     | `src/docreview360/sc/schema.py`, migrations                                        | `tests/sc/test_schema.py`                                      |
| New Project conditional Special Condition flow         | 161     | `frontend/pages/projects/new.tsx`                                                  | `cypress/e2e/sc_new_project.cy.ts`                             |
| Dedicated Special Condition-Intake page                | 162     | `frontend/pages/projects/[id]/sc-intake.tsx`                                       | `cypress/e2e/sc_intake_page.cy.ts`                             |
| Special Condition Workflow guards (review/notice/publish) | 163     | `src/docreview360/workflow/guards.py`                                              | `tests/sc/test_guards.py`                                      |
| SME task + banner                       | 164     | `src/docreview360/tasks/system_tasks.py` · `frontend/components/ProjectBanner.tsx` | `tests/sc/test_system_task.py` · `cypress/e2e/sc_banner.cy.ts` |
| Pre-fill Special Conditions Notice      | 165     | `src/docreview360/ext/sc_builder.py` (Task 137 integration)                        | `tests/sc/test_builder_prefill.py`                             |
| E2E Special Condition scenario                         | 166     | —                                                                                  | `tests/e2e/test_sc_flow.py`                                    |
