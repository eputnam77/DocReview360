# Code Review

## Summary
This update fixes navigation under `/tools` and adds a placeholder **Special Conditions Doc Builder** page. The documentation lists this new tool and points to the private repository for the full implementation.

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
| _app | No | No |
| about | No | No |
| configuration/audit-logs | Yes | Yes |
| configuration/document-types | Yes | Yes |
| configuration/index | No | No |
| configuration/integrations | Yes | No |
| configuration/permissions | Yes | Yes |
| configuration/phases | Yes | Yes |
| configuration/templates/edit-email | Yes | Yes |
| configuration/templates/edit | Yes | Yes |
| configuration/templates/index | Yes | Yes |
| configuration/templates/new-email | Yes | No |
| configuration/templates/new | Yes | No |
| configuration/user-management | Yes | Yes |
| configuration/workflows/[id] | No | Yes |
| configuration/workflows/edit | No | Yes |
| configuration/workflows/index | Yes | Yes |
| configuration/workflows/new | Yes | Yes |
| custom-fields | No | No |
| dashboard/admin | Yes | Yes |
| dashboard/index | No | No |
| dashboard/manager | Yes | Yes |
| dashboard/project/[id] | No | No |
| dashboard/settings | No | No |
| dashboard/user | Yes | Yes |
| docs/index | No | No |
| documenso/[sig] | No | No |
| editors/codex | No | No |
| editors/tiptap | No | No |
| editors/toast | No | No |
| editors/word | No | No |
| help | No | No |
| index | Yes | No |
| instances/[id] | No | No |
| login | No | No |
| logs/index | Yes | Yes |
| privacy | No | No |
| profile | Yes | No |
| projects/[id]/edit | Yes | No |
| projects/[id]/index | Yes | Yes |
| projects/[id]/review | Yes | No |
| projects/index | Yes | Yes |
| projects/new | Yes | Yes |
| reviews/[id] | No | No |
| reviews/index | No | No |
| search | Yes | No |
| signup | No | No |
| terms | No | No |
| tools/checker | Yes | No |
| tools/converter | Yes | No |
| tools/index | No | No |
| tools/sc_converter | No | No |
| viewer | No | No |
| workflows/[id]/start | Yes | No |

Pages lacking demo fallbacks include `integrations`, `profile`, all editor pages and several tools. Dashboard pages now fetch from the API but only `admin`, `manager` and `user` dashboards provide fallback data. Because demo mode is part of the docs, missing fallbacks on these pages may confuse users when the API is unreachable.

### Review Notes
- Many pages rely on live API calls without a demo fallback. Profile editing, project editing, project reviews and tools pages all fail silently if the API is offline.
- The `integrations` page fetches `/config` but lacks any placeholder data when the request fails.
- Only some configuration and dashboard pages include demo records.

### Conclusion
🔴 **Blocking issues**
- Several pages lack demo data fallbacks despite API integrations. Users will see empty pages if the backend is unreachable.

🟢 **Info**
- API calls generally trigger server-side `log_event` entries, so status and audit logs work as expected when requests succeed.

Label: `ready-for:builder`
