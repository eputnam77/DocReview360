# End-to-end (E2E) tests

This guide covers running the Playwright-powered E2E suite in a sandbox/CI-friendly way.

## Run locally

1. Install backend and frontend dependencies.
2. Run the E2E runner:

```bash
python scripts/run_e2e.py
```

Recommended quality gate run:

```bash
E2E_REQUIRE_PLAYWRIGHT=1 python scripts/run_e2e.py
```

This command:

1. Creates a run directory under `.e2e-runs/<run-id>/`.
2. Starts the backend and frontend in E2E mode.
3. Seeds deterministic test data.
4. Runs `pytest -m <marker-expression>` (defaults to `e2e`).
5. Shuts everything down.
6. Cleans the run directory on success (unless `KEEP_E2E_ARTIFACTS=1`).

## Test tiers

- `e2e_smoke`: small, release-gating browser/API flow set.
- `e2e_full`: smoke plus deeper permission/edge-case coverage.
- `e2e`: legacy umbrella marker for all E2E tests.

## Recommended run modes

Use these modes depending on intent:

1. Standard local run (allows Playwright-unavailable environments to skip browser tests):

```bash
python scripts/run_e2e.py
```

2. Strict verification run (recommended for CI and pre-merge checks):

```bash
E2E_REQUIRE_PLAYWRIGHT=1 python scripts/run_e2e.py
```

This fails fast if Playwright/browser binaries are unavailable instead of skipping E2E tests.

2.1 Smoke-only strict run (recommended PR gate):

```bash
E2E_REQUIRE_PLAYWRIGHT=1 E2E_TEST_MARK=e2e_smoke python scripts/run_e2e.py
```

2.2 Full strict run (recommended main/nightly):

```bash
E2E_REQUIRE_PLAYWRIGHT=1 E2E_TEST_MARK=e2e_full python scripts/run_e2e.py
```

3. Slow startup environments (frontend/backend takes longer to boot):

```bash
E2E_STARTUP_TIMEOUT_S=180 python scripts/run_e2e.py
```

4. Frontend mode override (if auto mode is not what you want):

```bash
E2E_FRONTEND_MODE=dev python scripts/run_e2e.py
E2E_FRONTEND_MODE=start python scripts/run_e2e.py
```

Default mode is `dev`.  
`start` uses the built frontend (`frontend/.next/BUILD_ID`); the runner builds it automatically if missing.
If `dev` fails to start (for example `spawn EPERM` in constrained Windows environments), the runner automatically falls back to `next build && next start`.

5. Dev engine override (for diagnosing Next.js runtime differences):

```bash
E2E_FRONTEND_DEV_ENGINE=webpack python scripts/run_e2e.py
E2E_FRONTEND_DEV_ENGINE=turbopack python scripts/run_e2e.py
```

Default dev engine is `webpack` for E2E stability in this repo.

6. Playwright artifact mode:

```bash
E2E_PLAYWRIGHT_ARTIFACTS=failure python scripts/run_e2e.py
E2E_PLAYWRIGHT_ARTIFACTS=off python scripts/run_e2e.py
E2E_PLAYWRIGHT_ARTIFACTS=on python scripts/run_e2e.py
```

Default is `failure` (screenshots/videos/traces only on failed tests).

PowerShell equivalents:

```powershell
$env:E2E_REQUIRE_PLAYWRIGHT = "1"; python scripts/run_e2e.py
$env:E2E_TEST_MARK = "e2e_smoke"; python scripts/run_e2e.py
$env:E2E_STARTUP_TIMEOUT_S = "180"; python scripts/run_e2e.py
$env:E2E_FRONTEND_DEV_ENGINE = "webpack"; python scripts/run_e2e.py
$env:E2E_PLAYWRIGHT_ARTIFACTS = "failure"; python scripts/run_e2e.py
$env:KEEP_E2E_ARTIFACTS = "1"; python scripts/run_e2e.py
```

## Sandbox/CI behavior

The runner sets `E2E_RUN_DIR` and configures all runtime outputs to land under it:

- Database: `.e2e-runs/<run-id>/db/`
- Uploads: `.e2e-runs/<run-id>/uploads/`
- Logs: `.e2e-runs/<run-id>/logs/`
- Temporary files: `.e2e-runs/<run-id>/tmp/`
- Test runner output: `.e2e-runs/<run-id>/artifacts/`

The backend binds to `0.0.0.0` while tests target `127.0.0.1`, which is reliable in the sandbox.

The runner also sets `DOCREVIEW360_ALLOW_ORIGINS` to the active frontend origin (`127.0.0.1`/`localhost` on the chosen port) so browser preflight requests are allowed during E2E.

## Debugging with text logs

On failures, the runner keeps logs under `.e2e-runs/<run-id>/logs/`:

- `backend.log`
- `frontend.log`

You can retain all artifacts by running:

```bash
KEEP_E2E_ARTIFACTS=1 python scripts/run_e2e.py
```

You can combine debug and strict mode:

```bash
KEEP_E2E_ARTIFACTS=1 E2E_REQUIRE_PLAYWRIGHT=1 E2E_TEST_MARK=e2e_full python scripts/run_e2e.py
```
