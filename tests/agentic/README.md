# Agentic QA Harness

This harness has two layers:

- API mode: fast in-process `TestClient` agents for deterministic workflow checks.
- Browser mode: watchable Playwright agents that use a live frontend and backend.

## API Mode

```powershell
.\.venv\Scripts\python.exe tests\agentic\runner.py --run-id local
```

## Browser Mode

Start the backend and frontend first, then run:

```powershell
.\.venv\Scripts\python.exe tests\agentic\runner.py `
  --ui `
  --run-id watch `
  --frontend-url http://localhost:3000 `
  --backend-url http://localhost:8000
```

Browser mode opens a headed Chromium window by default and slows actions down so
you can watch. Add `--headless` for CI-style runs, or tune `--slowmo-ms`.

Browser mode seeds through the live backend, logs in visibly, opens CKEditor,
edits the document, saves, tries to post a visible comment, and records an
approval through the API as the reviewer.

Bug reports are written as JSON under `tests/agentic/bug-reports` unless a
different `--bug-report-dir` is provided.

