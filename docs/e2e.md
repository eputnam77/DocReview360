# End-to-end (E2E) tests

This guide covers running the Playwright-powered E2E suite in a sandbox/CI-friendly way.

## Run locally

1. Install backend and frontend dependencies.
2. Run the E2E runner:

```bash
python scripts/run_e2e.py
```

This command:

1. Creates a run directory under `.e2e-runs/<run-id>/`.
2. Starts the backend and frontend in E2E mode.
3. Seeds deterministic test data.
4. Runs `pytest -m e2e`.
5. Shuts everything down.
6. Cleans the run directory on success (unless `KEEP_E2E_ARTIFACTS=1`).

## Sandbox/CI behavior

The runner sets `E2E_RUN_DIR` and configures all runtime outputs to land under it:

- Database: `.e2e-runs/<run-id>/db/`
- Uploads: `.e2e-runs/<run-id>/uploads/`
- Logs: `.e2e-runs/<run-id>/logs/`
- Temporary files: `.e2e-runs/<run-id>/tmp/`
- Test runner output: `.e2e-runs/<run-id>/artifacts/`

The backend binds to `0.0.0.0` while tests target `127.0.0.1`, which is reliable in the sandbox.

## Debugging with text logs

On failures, the runner keeps logs under `.e2e-runs/<run-id>/logs/`:

- `backend.log`
- `frontend.log`

You can retain all artifacts by running:

```bash
KEEP_E2E_ARTIFACTS=1 python scripts/run_e2e.py
```

The suite intentionally disables Playwright screenshots, videos, and traces to keep runs text-only.
