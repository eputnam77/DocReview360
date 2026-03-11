# /checklist-next — Pick and Implement Next Checklist Item

Read `RELEASE_CHECKLIST.md`, identify the next unchecked item, and implement
a minimal change to complete or advance it.

## Steps

1. **Find the next unchecked item:**
   ```bash
   grep -n '^\s*- \[ \]' RELEASE_CHECKLIST.md | head -5
   ```
   Select the first result. Note the section heading above it (use `grep -B20`
   to find the nearest `###` heading).

2. **Assess scope.** Read the item carefully. Classify it:
   - **Code change** — new feature, bug fix, or refactor in `src/` or `frontend/`.
   - **Script** — new utility under `scripts/`.
   - **Docs** — update to `README.md`, `docs/`, or `CHANGELOG.md`.
   - **Config** — change to `pyproject.toml`, `Dockerfile`, CI workflow.
   - **Manual / external** — requires human action outside the repo (e.g., branch
     protection, PyPI publish). Flag these and skip.

3. **Implement a minimal change.** Follow existing patterns:
   - New backend routes go in the appropriate sub-router, never in `api/__init__.py`.
   - Line length 100 (Black + Ruff).
   - Add `# SPDX-License-Identifier: MIT` to new `.py` files.
   - Conventional Commit message: `feat/fix/docs/refactor/test/chore`.

4. **Run the required checks:**
   ```bash
   DOCREVIEW360_ENV=dev pytest -q --tb=short -x --ignore=_debug_test.py \
       --ignore=tests/test_auth_repository.py 2>&1 | tail -20
   pre-commit run --all-files
   ```

5. **Mark the item done** in `RELEASE_CHECKLIST.md` by changing `[ ]` → `[x]`
   and appending the completion date: `(YYYY-MM-DD)`.

6. **Write a brief outcome summary** covering:
   - Item selected and its section
   - Files changed
   - Test result (pass/fail + count)
   - Any blockers or deferred sub-tasks

## Hard guardrails

- Do NOT auto-publish to PyPI, push Docker images, or make external API calls.
- Do NOT modify `.env` files or commit credentials.
- Do NOT skip pre-commit hooks (`--no-verify`).
- Items marked "Blocked on FSV" (Item 34) require the Federal Style Validator
  package to exist on PyPI first — skip them.
- High-risk files (`pyproject.toml` version bump, `LICENSE`, `SECURITY.md`)
  require human review before commit.
