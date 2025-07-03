# API Overview

DocuFlow exposes a JSON API that lets you manage projects, documents and approvals. The interactive documentation is available at `/docs` once the server is running. Below is a short summary of the main endpoints.

## Projects
- `GET /projects` – list all projects
- `POST /projects` – create a new project
- `GET /projects/{project_id}` – retrieve a single project
- `PUT /projects/{project_id}/priority` – update project priority
- `POST /projects/{project_id}/temporary` – assign a temporary user

## Documents
- `POST /documents/import` – import a file
- `GET /documents` – list documents
- `GET /documents/{doc_id}` – get a document
- `PUT /documents/{doc_id}` – update content
- `GET /documents/{doc_id}/export` – export to Markdown or DOCX

## Search
- `GET /search` – run a query
- `POST /search/saved` – save a search
- `GET /search/saved` – list saved searches

## Workflows and Approvals
- `POST /workflows` – create a workflow
- `POST /workflows/{wf_id}/advance` – move to the next step
- `POST /approvals` – request approval
- `PUT /approvals/{approval_id}` – update approval state

Authentication uses tokens returned by `/token` or `/oidc/token`. Include the token as `Bearer <token>` in the `Authorization` header.
