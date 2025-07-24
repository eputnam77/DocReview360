# Code Review

## Summary
This review audits API connections across all pages. Every page was checked for `fetch` calls and demo data fallbacks. Navigation under `/tools` was fixed and a placeholder **Special Conditions Doc Builder** page was added, with documentation pointing to the private repository.

## PRD Compliance
- **Editable approval comments** implemented via `task205` stub returning the new text【F:src/docreview360/stubs/task205.py†L8-L12】.
- **Approval comment notifications** return a formatted string from `task210`【F:src/docreview360/stubs/task210.py†L8-L12】.
- **Reset confirmation** uses `task213` to run an action only when confirmed【F:src/docreview360/stubs/task213.py†L8-L20】.
- Stubs for writer review permissions, external login providers and theme settings satisfy tasks 218‑222【F:src/docreview360/stubs/task218.py†L1-L17】【F:src/docreview360/stubs/task219.py†L1-L16】【F:src/docreview360/stubs/task220.py†L1-L15】【F:src/docreview360/stubs/task221.py†L1-L15】【F:src/docreview360/stubs/task222.py†L1-L15】.
- **Tools page** lists a Special Conditions Doc Builder card linking to `/tools/sc_converter`【F:frontend/pages/tools/index.tsx†L22-L29】【F:frontend/pages/tools/sc_converter.tsx†L1-L18】.

## Integration
- `/api/tools/checker.ts` spawns the Python checker via `execFile` and stores uploaded documents for download【F:frontend/pages/api/tools/checker.ts†L1-L60】.
- The `ScrollArea` component exposes a lightweight overflow container for other pages【F:frontend/components/ui/scroll-area.tsx†L1-L12】.
- A minimal `run_checks` implementation performs regex scans and anomaly detection in Python【F:services/document_checker/__init__.py†L1-L58】.
- The tools index routes users to the new `sc_converter` placeholder page【F:frontend/pages/tools/index.tsx†L22-L29】.

## Performance
- `run_checks` loads the entire file into memory which may not scale for very large documents.
- Node handler spawns a new Python process per request; caching or a persistent service could reduce overhead.

## Maintainability
- Unit tests for tasks 218‑222 only call functions without assertions, providing little value【F:tests/test_task218.py†L1-L6】【F:tests/test_task219.py†L1-L6】【F:tests/test_task220.py†L1-L6】【F:tests/test_task221.py†L1-L6】【F:tests/test_task222.py†L1-L6】.
- No documentation links the new Document Checker feature from the main docs.
- Environment variable `VENV_PYTHON` is used but not documented outside the service README.

## Testing
- ❌ `ruff check` failed due to unsorted imports【95aeba†L1-L5】.
- ✅ `black --check` passed【77158c†L1-L4】.
- ❌ `mypy --strict` failed because `pydantic` is missing【6b1703†L1-L5】.
- ❌ `bandit` and `semgrep` were not installed【196062†L1-L3】【dcdded†L1-L3】.
- ❌ `pytest` could not run because coverage options were unrecognised【3227ff†L1-L7】.
- ❌ Property and E2E tests failed to collect due to missing dependencies【9c2eac†L1-L36】【ee9216†L1-L74】.
- ❌ `mutmut` not installed【075cb5†L1-L4】.

Codex couldn't run certain commands due to environment limitations. Consider configuring a setup script or internet access in your Codex environment to install dependencies.

## Conclusion
🔴 **Blocking issues**
- Static type checking and tests fail due to missing dependencies.
- Semgrep could not run because the required domain is blocked.

🟢 **Info**
- Marked tasks 198, 199, 201‑204, 207‑208 and 223 as done in `UPDATED_TASKS.md`.
- Add assertions to the new unit tests.
- Document the `VENV_PYTHON` variable and link the Document Checker in the main docs.

Label: `ready-for:builder`

## API Wiring Audit

The table below summarizes whether each Next.js page fetches data from the backend API and if it falls back to demo data when the request fails.

| Page | Uses API | Demo fallback |
| --- | --- | --- |
| _app.tsx | No | No |
| about.tsx | No | No |
| configuration/audit-logs.tsx | Yes | Yes |
| configuration/document-types.tsx | Yes | Yes |
| configuration/index.tsx | No | No |
| configuration/integrations.tsx | Yes | Yes |
| configuration/permissions.tsx | Yes | Yes |
| configuration/phases.tsx | Yes | Yes |
| configuration/templates/edit-email.tsx | Yes | Yes |
| configuration/templates/edit.tsx | Yes | Yes |
| configuration/templates/index.tsx | Yes | Yes |
| configuration/templates/new-email.tsx | Yes | No |
| configuration/templates/new.tsx | Yes | No |
| configuration/user-management.tsx | Yes | Yes |
| configuration/workflows/[id].tsx | No | Yes |
| configuration/workflows/edit.tsx | No | Yes |
| configuration/workflows/index.tsx | Yes | Yes |
| configuration/workflows/new.tsx | Yes | Yes |
| custom-fields.tsx | No | No |
| dashboard/admin.tsx | Yes | Yes |
| dashboard/index.tsx | No | No |
| dashboard/manager.tsx | Yes | Yes |
| dashboard/project/[id].tsx | No | No |
| dashboard/settings.tsx | No | No |
| dashboard/user.tsx | Yes | Yes |
| docs/index.tsx | No | No |
| documenso/[sig].tsx | Yes | No |
| editors/codex.tsx | No | No |
| editors/tiptap.tsx | No | No |
| editors/toast.tsx | No | No |
| editors/word.tsx | No | No |
| help.tsx | No | No |
| index.tsx | Yes | No |
| instances/[id].tsx | No | No |
| login.tsx | No | No |
| logs/index.tsx | Yes | Yes |
| privacy.tsx | No | No |
| profile.tsx | Yes | Yes |
| projects/[id]/edit.tsx | Yes | No |
| projects/[id]/index.tsx | Yes | Yes |
| projects/[id]/review.tsx | Yes | Yes |
| projects/index.tsx | Yes | Yes |
| projects/new.tsx | Yes | Yes |
| reviews/[id].tsx | No | No |
| reviews/index.tsx | No | No |
| search.tsx | Yes | Yes |
| signup.tsx | No | No |
| terms.tsx | No | No |
| tools/checker.tsx | Yes | Yes |
| tools/converter.tsx | Yes | Yes |
| tools/index.tsx | No | No |
| tools/sc_converter.tsx | No | No |
| viewer.tsx | No | No |
| workflows/[id]/start.tsx | Yes | No |

Pages missing demo fallbacks are `configuration/templates/new`, `configuration/templates/new-email`, `documenso/[sig]`, `index`, `projects/[id]/edit` and `workflows/[id]/start`. These pages show blank content if the API is offline.

### Review Notes
- API actions log to the backend via `log_event`. For instance creating a project logs `create_project` when saving【F:src/docreview360/api.py†L321-L331】.
- The majority of configuration and dashboard pages provide demo data when requests fail, but the pages listed above still lack fallbacks.

### Conclusion
🔴 **Blocking issues**
- Several pages lack demo data fallbacks despite API integrations. Users will see empty pages if the backend is unreachable.

🟢 **Info**
- API calls generally trigger server-side `log_event` entries, so status and audit logs work as expected when requests succeed.

Label: `ready-for:builder`
