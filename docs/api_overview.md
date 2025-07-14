# API Overview

DocReview360 exposes a JSON API that lets you manage projects, documents and approvals. The interactive documentation is available at `/docs` once the server is running. Below is a short summary of the main endpoints.

## Projects
- `GET /projects` – list all projects
- `POST /projects` – create a new project
- `GET /projects/{project_id}` – retrieve a single project
- `GET /projects/{project_id}/workflow` – get the project's workflow
- `PUT /projects/{project_id}/priority` – update project priority
- `POST /projects/{project_id}/temporary` – assign a temporary user

## Documents
- `POST /documents/import` – import a file
- `POST /documents/tiptap` – import content from the TipTap editor
- `GET /documents` – list documents
- `GET /documents/{doc_id}` – get a document
- `PUT /documents/{doc_id}` – update content
- `POST /documents/{doc_id}/comments` – add a comment
- `GET /documents/{doc_id}/comments` – list comments
- `GET /documents/{doc_id}/export` – export to Markdown or DOCX

## Archive
- `POST /archive/{doc_id}` – archive a document in multiple formats
- `GET /archive` – list archived files
- `GET /archive/{archive_id}` – retrieve a single archive

## Search
- `GET /search` – run a query
- `POST /search/saved` – save a search
- `GET /search/saved` – list saved searches
- `GET /search/export` – download results as JSON or CSV
- `GET /search/stats` – return query counts

## Workflows and Approvals
- `POST /workflows` – create a workflow
- `GET /workflows/{wf_id}` – retrieve a workflow
- `POST /workflows/{wf_id}/assign` – assign a reviewer
- `POST /workflows/{wf_id}/advance` – move to the next step
- `POST /approvals` – request approval
- `GET /approvals` – list approvals
- `GET /approvals/{approval_id}` – retrieve an approval
- `PUT /approvals/{approval_id}` – update approval state
- `POST /approvals/{approval_id}/sign` – start a signature request

## Document Types
- `POST /document-types` – create a type
- `GET /document-types` – list types
- `GET /document-types/export` – download all types as JSON
- `POST /document-types/import` – replace types from a JSON file
- `GET /document-types/{name}` – retrieve a type by name
- `PUT /document-types/{name}` – update a type
- `DELETE /document-types/{name}` – remove a type

## AI Helpers
- `POST /ai/rewrite` – rewrite provided text
- `POST /ai/summarize` – return a one sentence summary

## Signatures
- `POST /sign/{doc_id}` – create a Documenso signature request
- `POST /sign/{sig_id}/complete` – mark a signature as signed
- `GET /sign/{sig_id}` – check signature status
- `POST /approvals/{approval_id}/sign` – sign a workflow approval
- `POST /hooks/documenso` – webhook for signature callbacks

## Plugins
- `GET /plugins` – list registered plugins
- `POST /plugins` – load plugins from a module
- `PUT /plugins/{name}/enable` – enable a plugin
- `PUT /plugins/{name}/disable` – disable a plugin
- `DELETE /plugins/{name}` – unregister a plugin

## Logs and Reporting
- `GET /logs` – retrieve event logs
- `GET /api/audit` – alias for `/logs` used by the dashboard
- `GET /reports/summary` – counts of projects, documents and approvals
- `GET /metrics/summary` – Prometheus style metrics
- `GET /reports/summary.csv` – download the summary report
- `GET /reports/dashboard` – per-project dashboard data
- `GET /dashboard/widgets` – assignment and approval counts

## Configuration and Status
- `GET /config` – return the current configuration
- `PUT /config` – update and persist settings
- `GET /status/public` – minimal health data
- `GET /status/internal` – extended status for administrators

## Authentication
- `POST /token` – issue a JWT access token
- `POST /oidc/token` – issue an OpenID Connect token
- `GET /me` – retrieve the authenticated user
- `GET /oidc/me` – user details for the OIDC flow
Authentication uses the returned token as `Bearer <token>` in the
`Authorization` header.

## Admin
- `GET /admin/panel` – simple admin-only check

## WebSockets
- `WS /ws/dashboard` – live dashboard statistics
- `WS /ws/logs` – stream log events

## GraphQL
Read-only queries are available via a small GraphQL layer. See
[Latest Features](latest_features.md) for example usage of `execute_query`.
