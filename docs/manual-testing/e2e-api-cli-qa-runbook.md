# DocReview360 End-to-End QA Runbook (API + CLI)

Use this runbook to exercise the app without the UI. It covers happy paths, edge cases, and admin flows. Log every step in a single cumulative log artifact.

## Goals

- Validate core workflows end to end.
- Verify role boundaries and permissions.
- Detect regressions across API and CLI interfaces.
- Capture gaps and design issues for remediation.

## Required Artifacts

- Cumulative log file (single file per run).
- Request/response snippets with redacted secrets.
- Any files created or modified by the test run.

## Environment Setup

1. Pick a base URL.
   - Example: `http://127.0.0.1:8001`
2. Identify credentials for:
   - Admin user
   - Standard user
3. Ensure databases are accessible.
4. Confirm the server is running.

## Logging Format (Use After Every Step)

Use this exact structure:

```
Step <n>: <short description>
a) Command/Request: <command or METHOD /path + payload>
b) Files touched: <paths or "none">
c) Observed output: <status, response body, CLI output>
d) Warnings/issues: <none or details>
```

## Common Variables

- `BASE_URL`
- `ADMIN_USER`, `ADMIN_PASS`
- `USER_A`, `USER_A_PASS`
- `USER_B`, `USER_B_PASS`

## Preflight Checks

1. Health checks
   - `GET /ping`
   - `GET /health`
2. Auth readiness
   - `POST /token` with admin credentials
   - `POST /token` with regular credentials
3. Profile access
   - `GET /users/me` (token required)
   - `GET /profile` (token required)

## Authentication and Session

1. Login (admin)
   - `POST /token` or `POST /login`
2. Login (regular user)
   - `POST /token`
3. Invalid login attempts
   - Wrong password
   - Missing username
4. Logout
   - `POST /logout`
5. Token reuse
   - Reuse token after logout (expect failure or invalidation)

## Project Lifecycle

1. Create a project (admin)
   - `POST /projects`
   - Include name, document type, priority, assigned users if supported
2. List projects
   - `GET /projects`
   - Verify new project appears
3. Retrieve project
   - `GET /projects/{id}`
4. Update project fields
   - `PUT /projects/{id}` (name, priority, status, metadata)
5. Assign and unassign users
   - If API supports assignments, use the project assignment endpoints
6. Temporary project state
   - `POST /projects/{id}/temporary`
7. Project preferences
   - `GET /projects/{id}/preferences`
   - `PUT /projects/{id}/preferences`

## Document Flow (TipTap + Imports)

1. Create TipTap document
   - `POST /documents/tiptap`
2. View document details
   - `GET /documents/{doc_id}`
3. Update document content
   - `PUT /documents/{doc_id}`
4. Add a revision
   - `POST /documents/{doc_id}/revisions`
   - `GET /documents/{doc_id}/revisions`
5. Add comments
   - `POST /documents/{doc_id}/comments`
   - `GET /documents/{doc_id}/comments`
6. Import a document (DOCX/PDF/MD)
   - `POST /documents/import`
7. Style validation (FedStyleValidator)
   - Import a short DOCX file
   - Confirm style issues appear when the validator is available
   - If the validator is missing, confirm heuristic scoring still returns a value
8. Validate audit log per document
   - `GET /documents/{doc_id}/audit`
9. Export document
   - `GET /documents/{doc_id}/export`

## Workflow and Approvals

1. List workflow roles
   - `GET /workflow_roles`
2. Create a workflow
   - `POST /workflows`
3. Start workflow
   - `POST /workflows/{id}/start`
   - Omit `title` and confirm the server assigns a default
4. Assign reviewer
   - `POST /workflows/{id}/assign`
5. Advance workflow phase
   - `POST /workflows/{id}/advance`
6. Create approval
   - `POST /approvals`
7. List approvals
   - `GET /approvals`
8. Update approval status
   - `PUT /approvals/{approval_id}`

## Signatures and Verification

1. Initiate signature
   - `POST /sign/{doc_id}`
2. Complete signature
   - `POST /sign/{sig_id}/complete`
3. Verify signature status
   - `GET /sign/{sig_id}`
4. Document signature verification
   - `GET /documents/{doc_id}/verify-signature`
5. Duplicate sign attempt
   - Call `POST /approvals/{approval_id}/sign` twice
   - Expect `409` on the second call

## Reviews

1. Create review
   - `POST /projects/{project_id}/reviews`
2. List reviews
   - `GET /projects/{project_id}/reviews`

## ML Endpoints and Rate Limits

1. Quality assessment
   - `POST /ml/quality`
2. Compliance evaluation
   - `POST /ml/compliance`
3. Routing recommendation
   - `POST /ml/routing`
4. Signature anomaly scoring
   - `POST /ml/signature`
5. Rate limit check
   - Call the same ML endpoint 6+ times in under 60 seconds
   - Expect `429` after the limit is reached

## Search and Saved Searches

1. Search documents
   - `GET /search`
2. Export search results
   - `GET /search/export`
3. Save a search
   - `POST /search/saved`
4. List saved searches
   - `GET /search/saved`
5. Search stats
   - `GET /search/stats`

## Dashboards and Reports

1. User dashboard
   - `GET /dashboard/user`
2. Manager dashboard
   - `GET /dashboard/manager`
3. Admin dashboard
   - `GET /dashboard/admin`
4. Dashboard widgets
   - `GET /dashboard/widgets`
5. Report summaries
   - `GET /reports/summary`
   - `GET /reports/throughput`
   - `GET /reports/workload`

## Document Types and Templates

1. Create document type
   - `POST /document-types`
2. List document types
   - `GET /document-types`
3. Update document type
   - `PUT /document-types/{name}`
4. Usage metrics
   - `GET /document-types/{name}/usage`
5. Export and import types
   - `GET /document-types/export`
   - `POST /document-types/import`
6. Template list and detail
   - `GET /templates`
   - `GET /templates/{name}`
7. Create template
   - `POST /templates`
8. Approve and retire template
   - `POST /templates/{name}/approve`
   - `POST /templates/{name}/retire`

## Plugins

1. List plugins
   - `GET /plugins`
2. Install plugin
   - `POST /plugins`
3. Enable/disable plugin
   - `PUT /plugins/{name}/enable`
   - `PUT /plugins/{name}/disable`
4. Delete plugin
   - `DELETE /plugins/{name}`
5. Marketplace checks
   - `GET /plugin-marketplace`
   - `POST /plugin-marketplace/install`

## Phases and Workflow Catalog

1. Create phase
   - `POST /phases`
2. List phases
   - `GET /phases`
3. Update phase
   - `PUT /phases/{name}`
4. Phase usage
   - `GET /phases/{name}/usage`
5. Delete phase
   - `DELETE /phases/{name}`
6. List workflows
   - `GET /workflows`
7. Retrieve workflow
   - `GET /workflows/{wf_id}`

## Archive

1. Archive a document
   - `POST /archive/{doc_id}`
2. List archives
   - `GET /archive`
3. Retrieve archive details
   - `GET /archive/{archive_id}`
4. Export archive report
   - `GET /archive/{archive_id}/report/{fmt}`

## Audit Logs and Integrity

1. API audit log
   - `GET /api/audit`
2. Logs export
   - `GET /logs/export`
3. CLI hash chain
   - `docreview360 logs hash-chain`
   - (Optional) `docreview360 logs hash-chain --key log_chain-<timestamp>.json`
4. CLI verify chain
   - `docreview360 logs verify-chain`
   - (Optional) `docreview360 logs verify-chain --key log_chain-<timestamp>.json`

## Configuration and Status

1. Read config
   - `GET /config`
2. Update config (admin only)
   - `PUT /config`
3. Signature provider
   - `GET /signature-provider`
   - `PUT /signature-provider`
4. Public/internal status
   - `GET /status/public`
   - `GET /status/internal`

## RBAC and Admin Operations

1. Disable a user (admin)
   - `POST /admin/users/{username}/status`
2. RBAC CLI
   - `docreview360 rbac set-role` (alias of `rbac-admin`)
   - `docreview360 rbac show`
   - `docreview360 rbac-admin set-role` (explicit command)
   - `docreview360 rbac-admin show`
3. Permission checks
   - Repeat key endpoints as regular user and expect 403 or limited data.

## Edge Cases and Failure Paths

1. Missing required fields
2. Invalid IDs (project, document, approval)
3. Rapid sequential updates (idempotency check)
4. Pagination and filtering (if supported)
5. Large payloads (document size limits)
6. Unsupported MIME types
7. Restart server and recheck data persistence
8. ML model integrity
   - If `/ml/signature` fails on startup, regenerate the model and retry

## CLI Coverage

1. Init config
   - `docreview360 init`
2. Validate ML models (if present)
   - `docreview360 validate --ml <path>`
3. Export/import instance data
   - `docreview360 migrate export`
   - `docreview360 migrate import`

## Final Checks

1. Verify dashboards reflect latest actions.
2. Confirm audit logs match user actions.
3. Confirm workflow phase and approvals align.
4. Ensure role boundaries are enforced.

## Output

- Provide the cumulative log file.
- Provide a summary of failures, inconsistencies, and design smells.
- Provide recommended fixes or follow-up tasks.
