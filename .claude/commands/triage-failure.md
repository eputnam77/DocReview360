# /triage-failure — Failing Test Triage

Triage a failing test or CI failure in DocReview360. Given a test name, error message,
or stack trace, investigate the root cause and propose the smallest patch.

## Steps

1. **Identify the failure.** If the user did not provide a specific test, run:
   ```bash
   DOCREVIEW360_ENV=dev pytest -q --tb=short -x 2>&1 | head -60
   ```
   to find the first failure.

2. **Read the failing test** to understand what it expects. Locate it under `tests/`.

3. **Read the relevant source file(s)** implicated by the stack trace.

4. **Check known pre-existing failures:**
   - `tests/test_coverage_gaps.py` — 19 failures testing no-auth routes that now require auth (do not fix these; they are known).
   - `tests/test_role_403_mfa.py` — 2 failures requiring `pyotp` (install or skip).
   - Test ordering / state-pollution failures: run the test in isolation first:
     ```bash
     DOCREVIEW360_ENV=dev pytest tests/<file>::<test_name> -v --tb=long
     ```

5. **Determine root cause.** Common causes:
   - Route moved to a sub-router but test still calls the old path.
   - Auth guard added to an endpoint the test does not authenticate.
   - Model field renamed (e.g., `default_template_id` → `default_workflow_template_id`).
   - Test state pollution from a prior test that mutates global in-memory state.
   - Missing fixture or import after a module was refactored into a package.

6. **Propose a minimal patch.** Edit only the test or the source, not both, unless
   the source has a genuine bug. Prefer adding auth headers to the test over removing
   guards from the source.

7. **Verify the fix** by running the specific test again:
   ```bash
   DOCREVIEW360_ENV=dev pytest tests/<file>::<test_name> -v
   ```

8. **Run the full suite** (optional, before committing):
   ```bash
   DOCREVIEW360_ENV=dev pytest -q --tb=no --ignore=_debug_test.py --ignore=tests/test_auth_repository.py 2>&1 | tail -5
   ```

## Key conventions

- Admin headers pattern: create user + `rbac.add_role("alice", "admin")` + `Authorization: Bearer <token>`.
- All routes require `Authorization: Bearer <token>` or httpOnly cookie.
- New endpoints go in sub-routers under `src/docreview360/api/`, not in `api/__init__.py`.
- `DocumentModel` has no `title` field — use `document.id`.
