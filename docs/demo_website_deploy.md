# DocReview360 demo on a single domain

This guide shows how to run the DocReview360 demo at
`https://ericputnam.com/apps/docreview360` with HTTPS.

## Decision: single instance (recommended)

Use a single backend instance for the demo.

Reason:
- Documents, approvals, comments, reviews, and signatures are in memory.
- Multiple instances will not share that data.
- A restart clears in-memory data.

If you need scale or HA, you must move those features to shared storage and
add a distributed signature provider.

## What the demo supports

- Login with demo users: `alice/password` and `bob/password`
- Create projects and upload/edit documents
- Run approvals and sandbox signatures

## URL layout

Keep the backend on the same host as the frontend so cookies work.

Use one of these layouts:

1) Simple path-only layout (no code changes, can conflict with other apps)
- Frontend: `https://ericputnam.com/apps/docreview360`
- Backend: `https://ericputnam.com/docreview360-api`
- Root `/api/*` is reserved for this app's Next.js API routes

2) Multi-app layout (recommended if you host multiple Next.js apps)
- Frontend: `https://ericputnam.com/apps/docreview360`
- Backend: `https://ericputnam.com/apps/docreview360-api`
- Requires Next.js basePath updates (see below)

## Environment variables

Create `.env` at the repo root (server side).

```
DOCREVIEW360_ENV=stage
DOCREVIEW360_SECRET_KEY=change-this
DOCREVIEW360_OIDC_SECRET_KEY=change-this-too
DOCREVIEW360_SEED_DEMO_USERS=true
DOCREVIEW360_REQUIRE_MFA=false
DOCREVIEW360_ALLOW_ORIGINS=https://ericputnam.com
```

Frontend build-time env:

```
NEXT_PUBLIC_API_BASE=https://ericputnam.com/docreview360-api
```

If you use the multi-app layout, set:

```
NEXT_PUBLIC_API_BASE=https://ericputnam.com/apps/docreview360-api
```

## Option 1: Simple path-only layout (no code changes)

Use this if you do not host other Next.js apps on the same domain.

### 1) Build and run backend

```
poetry install --with dev
poetry sync --with dev
uvicorn docreview360.api:app --host 127.0.0.1 --port 8000
```

### 2) Build and run frontend

```
cd frontend
npm ci
set NEXT_PUBLIC_API_BASE=https://ericputnam.com/docreview360-api
npm run build
npm run start -- -p 3000
```

### 3) Reverse proxy (Caddy example)

```
ericputnam.com {
  encode gzip

  # Backend API
  handle_path /docreview360-api/* {
    reverse_proxy 127.0.0.1:8000
  }

  # Next.js API routes for this app
  handle_path /api/* {
    reverse_proxy 127.0.0.1:3000
  }

  # Frontend app under /apps/docreview360
  handle_path /apps/docreview360/* {
    reverse_proxy 127.0.0.1:3000
  }
}
```

Notes:
- `/api/*` is reserved for this app's Next.js API routes.
- This can conflict if other apps also use `/api/*`.

## Option 2: Multi-app layout (requires basePath updates)

Use this if you host multiple apps under `/apps/*`.

### 1) Set Next.js basePath

Edit `frontend/next.config.js`:

```
const nextConfig = {
  reactStrictMode: true,
  experimental: { optimizeCss: true },
  basePath: "/apps/docreview360",
  assetPrefix: "/apps/docreview360",
};
```

### 2) Update frontend fetches that use `/api/*`

Search and replace:
- `fetch("/api/...")` -> `fetch(`${API}/...`)`

This prevents calls from going to the root `/api/*` path.

### 3) Build and run frontend

```
cd frontend
npm ci
set NEXT_PUBLIC_API_BASE=https://ericputnam.com/apps/docreview360-api
npm run build
npm run start -- -p 3000
```

### 4) Reverse proxy (Caddy example)

```
ericputnam.com {
  encode gzip

  # Backend API for DocReview360
  handle_path /apps/docreview360-api/* {
    reverse_proxy 127.0.0.1:8000
  }

  # Frontend app under /apps/docreview360
  handle_path /apps/docreview360/* {
    reverse_proxy 127.0.0.1:3000
  }
}
```

## Optional: run the worker

The demo works without the worker. Run it if you want reminders/escalations.

```
celery -A docreview360.celery_app worker --loglevel=info
```

## Quick verification

1) Open `https://ericputnam.com/apps/docreview360/login`
2) Log in as `alice/password`
3) Create a project and upload a file
4) Start an approval and use the sandbox signature

## Limitations to call out in the demo

- In-memory data resets on restart.
- Sandbox signatures are simulated.
- Document checker uses a fallback validator if FedStyleValidator is not installed.

