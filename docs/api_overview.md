# API overview

DocReview360 exposes a JSON REST API for projects, documents, workflows, and approvals.

Interactive documentation is at `/docs` once the server is running. This page covers authentication and the endpoints you are most likely to need.

## Authenticate

Request a token, then send it as a bearer token on every call.

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/token \
  -d "username=alice&password=password" | jq -r .access_token)

curl http://127.0.0.1:8000/projects -H "Authorization: Bearer $TOKEN"
```

| Endpoint | Purpose |
| --- | --- |
| `POST /token` | Issue a JWT access token |
| `POST /oidc/token` | Issue an OpenID Connect token |
| `GET /me` | Return the authenticated user |
| `GET /oidc/me` | Return user details for the OIDC flow |

Cookie-based auth is also supported. It requires an `X-CSRF-Token` header matching the `csrf_token` cookie.

## Versioning

Endpoints are available unprefixed. Versioned aliases exist at `/api/v1/*` and behave identically. See [API versioning](api_versioning.md) for the deprecation policy.

## Projects

| Endpoint | Purpose |
| --- | --- |
| `GET /projects` | List projects |
| `POST /projects` | Create a project |
| `GET /projects/{project_id}` | Retrieve a project |
| `GET /projects/{project_id}/workflow` | Get the project's workflow |
| `PUT /projects/{project_id}/priority` | Update priority |
| `POST /projects/{project_id}/temporary` | Assign a temporary user |

## Documents

| Endpoint | Purpose |
| --- | --- |
| `POST /documents/import` | Import a file |
| `POST /documents/tiptap` | Import TipTap editor content. Set `link_duplicates=true` to reuse an existing match |
| `GET /documents` | List documents |
| `GET /documents/{doc_id}` | Retrieve a document |
| `PUT /documents/{doc_id}` | Update content |
| `POST /documents/{doc_id}/comments` | Add a comment |
| `GET /documents/{doc_id}/comments` | List comments |
| `GET /documents/{doc_id}/export` | Export to Markdown, text, HTML, DOCX, PDF, JSON, or XML |

## Workflows and approvals

| Endpoint | Purpose |
| --- | --- |
| `POST /workflows` | Create a workflow |
| `GET /workflows/{wf_id}` | Retrieve a workflow |
| `POST /workflows/{wf_id}/assign` | Assign a reviewer |
| `POST /workflows/{wf_id}/advance` | Move to the next step |
| `POST /approvals` | Request approval |
| `GET /approvals` | List approvals |
| `GET /approvals/{approval_id}` | Retrieve an approval |
| `PUT /approvals/{approval_id}` | Update approval state |
| `POST /approvals/{approval_id}/sign` | Start a signature request |

## Signatures

| Endpoint | Purpose |
| --- | --- |
| `POST /sign/{doc_id}` | Create a signature request |
| `POST /sign/{sig_id}/complete` | Mark a signature as signed |
| `GET /sign/{sig_id}` | Check signature status |
| `GET /documents/{doc_id}/verify-signature` | Validate document signatures |
| `GET /documents/{doc_id}/verify-signature/stream` | Stream verification progress |
| `POST /hooks/documenso` | Receive Documenso callbacks. Registered only when `SIGNATURE_PROVIDER=documenso` |

### Stream verification progress

Verification can take a while, so results stream as server-sent events.

```javascript
const evt = new EventSource('/documents/123/verify-signature/stream');
evt.onmessage = (e) => console.log(JSON.parse(e.data));
```

```python
import requests

url = "http://127.0.0.1:8000/documents/123/verify-signature/stream"
with requests.get(url, stream=True) as r:
    for line in r.iter_lines():
        if line:
            print(line.decode())
```

## Search

| Endpoint | Purpose |
| --- | --- |
| `GET /search` | Run a query |
| `POST /search/saved` | Save a search |
| `GET /search/saved` | List saved searches |
| `GET /search/export` | Download results as JSON or CSV |
| `GET /search/stats` | Return query counts |

## Document types

| Endpoint | Purpose |
| --- | --- |
| `GET /document-types` | List types |
| `POST /document-types` | Create a type |
| `GET /document-types/{name}` | Retrieve a type |
| `PUT /document-types/{name}` | Update a type |
| `DELETE /document-types/{name}` | Remove a type |
| `GET /document-types/export` | Download all types as JSON |
| `POST /document-types/import` | Replace types from JSON |

## Archive

| Endpoint | Purpose |
| --- | --- |
| `POST /archive/{doc_id}` | Archive a document in multiple formats |
| `GET /archive` | List archived files |
| `GET /archive/{archive_id}` | Retrieve an archive |

## Reporting and logs

| Endpoint | Purpose |
| --- | --- |
| `GET /logs` | Retrieve event logs |
| `GET /api/audit` | Dashboard alias for `/logs` |
| `GET /reports/summary` | Counts of projects, documents, and approvals |
| `GET /reports/summary.csv` | Download the summary report |
| `GET /reports/dashboard` | Per-project dashboard data |
| `GET /dashboard/widgets` | Assignment and approval counts |
| `GET /dashboard/doc-types` | Active project counts by document type |
| `GET /metrics/summary` | Prometheus-style metrics |

## Webhooks

Register a callback URL to receive events:

```bash
curl -X POST http://127.0.0.1:8000/webhooks/subscribe \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/hooks", "events": ["verification.completed"]}'
```

After each verification run, DocReview360 posts:

```json
{
  "event": "verification.completed",
  "payload": { "doc_id": "123", "status": "pass", "details": [] }
}
```

## Plugins

| Endpoint | Purpose |
| --- | --- |
| `GET /plugins` | List registered plugins |
| `POST /plugins` | Load plugins from a module |
| `PUT /plugins/{name}/enable` | Enable a plugin |
| `PUT /plugins/{name}/disable` | Disable a plugin |
| `DELETE /plugins/{name}` | Unregister a plugin |

## AI helpers

Optional and off by default.

| Endpoint | Purpose |
| --- | --- |
| `GET /ai/key` | Check whether the rewrite key is configured |
| `PUT /ai/key` | Store or clear the rewrite key |
| `POST /ai/rewrite` | Rewrite text |
| `POST /ai/summarize` | Return a one-sentence summary |

## Configuration and status

| Endpoint | Purpose |
| --- | --- |
| `GET /config` | Return the current configuration |
| `PUT /config` | Update and persist settings |
| `GET /status/public` | Minimal health data |
| `GET /status/internal` | Extended status for administrators |
| `GET /admin/panel` | Admin-only access check |

## WebSockets

| Endpoint | Purpose |
| --- | --- |
| `WS /ws/dashboard` | Live dashboard statistics |
| `WS /ws/logs` | Stream log events |

WebSocket routes do not appear in the OpenAPI schema. For reverse-proxy configuration, see the [WebSocket proxy guide](websocket_proxy_guide.md).

## GraphQL

A small read-only GraphQL layer is available with the `graphql` extra.
