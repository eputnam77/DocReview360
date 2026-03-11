# API Versioning Strategy

## Overview

DocReview360 follows a **URL-path versioning** strategy with a permanent
compatibility guarantee for each stable version:

```
/api/v1/...   ← current stable (v0.x releases)
/api/v2/...   ← next major (when breaking changes accumulate)
```

All v1 endpoints are served at their **current unversioned path** (e.g.
`/documents/{id}`) as well as the versioned alias (`/api/v1/documents/{id}`)
so that existing integrations continue to work without changes.

---

## Versioning principles

### 1. Additive-only changes within a major version

The following changes are **non-breaking** and may be introduced at any point
within a major version:

- New optional query parameters
- New optional request body fields (with documented defaults)
- New response body fields (clients must ignore unknown fields)
- New endpoints
- New 2xx status codes on existing endpoints (if semantically equivalent)

### 2. Breaking changes require a new major version

The following changes are **breaking** and will not be made to an existing
major version:

- Removing or renaming an existing field
- Changing the type of an existing field
- Changing the URL path structure
- Changing the HTTP method of an endpoint
- Removing an endpoint
- Changing authentication requirements (adding or removing required auth)
- Changing a 2xx response to a 4xx/5xx for valid, previously-accepted inputs

### 3. Deprecation policy

Before removing a field or endpoint, it must be:

1. Marked deprecated in the OpenAPI schema (`deprecated: true`).
2. Added to the `Deprecation-Date` response header on affected endpoints.
3. Kept functional for **at minimum two minor releases** after the deprecation
   announcement.
4. Removed only in the next major version.

---

## Version header

All responses include:

```
X-DocReview360-API-Version: 1.0
```

Clients may send `Accept-Version: 1` to explicitly request API v1 behaviour.

---

## Implementation

### Current routing structure

Sub-routers are registered in `src/docreview360/api/__init__.py`:

```python
app.include_router(branches_router, prefix="/api/v1")
app.include_router(legal_router,    prefix="/api/v1")
# ... etc
```

The unversioned aliases (backward compat) are registered at the root prefix
until v2 is released:

```python
app.include_router(branches_router)  # /documents/{id}/branches
```

### Adding a v2 endpoint

1. Create `src/docreview360/api/v2/` with a new router module.
2. Register with `prefix="/api/v2"`.
3. Keep v1 endpoints untouched.

### OpenAPI schema per version

Access version-specific OpenAPI schemas at:

- `/api/v1/openapi.json` — stable v1 schema
- `/openapi.json` — current (same as v1 for now)

---

## Gateway compatibility

DocReview360 is compatible with the following API gateways and service meshes:

| Gateway / Mesh     | Notes                                                          |
|--------------------|----------------------------------------------------------------|
| AWS API Gateway    | HTTP API type; use path-based routing for `/api/v1/`           |
| Kong               | Route by path prefix; enable CORS plugin                       |
| Apigee             | Version header `X-DocReview360-API-Version` passthrough needed |
| Istio              | VirtualService path prefix routing; configure retries via DR   |
| Nginx (standalone) | See `nginx/nginx.conf`; add `/api/v1/` prefix location block   |

### Rate limiting per version

API v1 shares rate limits with the unversioned path (same counters). When v2
launches, separate limits will be configurable via
`DOCREVIEW360_RATE_LIMIT_V1_DEFAULT` and `DOCREVIEW360_RATE_LIMIT_V2_DEFAULT`.

---

## Changelog

| Version | Date       | Changes                              |
|---------|------------|--------------------------------------|
| 1.0.0   | 2026-01-01 | Initial stable release               |
| 1.1.0   | 2026-03-10 | Added branches, legal hold, config, feature flags, custom workflows/fields, i18n, branding endpoints |
