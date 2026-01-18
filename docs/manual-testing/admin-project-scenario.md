# Admin Project Scenario – Manual Run

## Environment setup

1. Started the FastAPI backend with host binding so the browser container could reach it:
   ```bash
   uvicorn docreview360.api:app --reload --host 0.0.0.0 --port 8000
   ```
2. Ran the Next.js frontend with `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000`.
3. Verified the browser container could reach both ports via Playwright.

## Scenario steps & findings

### 1. Log in as admin (`alice/password`)

* Outcome: ✅ Login succeeds and the projects list renders.
* Issues:
  * Multiple `401 Unauthorized` responses are emitted before the credentialed request succeeds, because the UI pre-fetches `/users/me` and `/dashboard/visibility` without a token. These eventually succeed but flood the console/server logs. 【b70f97†L19-L70】

### 2. Create a new project

* Actions:
  * Navigated to **Create New Project**.
  * Selected the only document type returned by the API (`Test Document Type`).
  * Entered `AC-TEST-001` and the title `Automation Scenario Test Document`.
  * Picked the first phase option (`draft`) and submitted the form.
* Outcome: ✅ Backend returns `201 Created` and stores the project. 【b70f97†L104-L113】
* Issues:
  * The projects table is filtered by the logged-in username (`?user=alice`). The new project is assigned to the SME name entered in the form (`Automation SME`), so it never appears in the list despite being created. 【F:frontend/pages/projects/index.tsx†L88-L101】【65755d†L6-L13】

### 3. Open project detail pages

* Attempted to open both the demo project (`/projects/demo-project`) and the newly created project (`/projects/ba3b1a1b-b64b-43d0-a8a1-49d9d9d0d43b`).
* Outcome: ❌ The page crashes with `ReferenceError: Table is not defined` before any content renders. 【F:frontend/pages/projects/[id]/index.tsx†L752-L801】
* Evidence: ![Project detail runtime error](browser:/invocations/cgheluua/artifacts/artifacts/new_project.png)
* Root cause: `Table`, `TableHeader`, `TableBody`, etc. are used but never imported in `pages/projects/[id]/index.tsx`, so runtime evaluation fails immediately.

### 4. Edit the project

* Blocked: the detail page crash prevents access to the **Edit Project** link, so no edits can be made.

### 5. Dashboard review

* Outcome: ✅ `/dashboard` loads, but all metrics are hard-coded demo values, so the new project is not reflected.

### 6. Open TipTap editor & Documenso signing

* Blocked: the same project-detail crash prevents navigation to the editor and approvals sections, so the editor cannot open and the Documenso signing flow cannot start.

## Summary of major issues

1. **Project detail page hard-crashes** because `Table` components are referenced without being imported.
2. **Project list filter hides new projects** unless their `user` matches the logged-in username.
3. **Pre-login API calls emit 401 noise**, cluttering logs during authentication.
