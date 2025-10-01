# Deploying DocReview360

This quick note explains how to run the container on common free-tier platforms.
The image expects a `PORT` environment variable supplied by the host.

1. **Render** – add a Postgres database service and set `DATABASE_URL` to the
   connection string. The platform automatically provides `PORT`.
2. **Heroku** – provision a Postgres add-on and enable the `PORT` config
   variable. The app will bind to it without further changes.
3. **Fly.io** – create a Postgres instance with `fly postgres`. Define `DATABASE_URL`
   and `PORT` in the app configuration.
4. **Railway** – add a Postgres plugin and copy the `DATABASE_URL`. Railway
   injects `PORT` when the container starts.

The Dockerfile installs backend and frontend dependencies and builds the Next.js
UI so the resulting image can run on these providers with minimal setup.

## Installing Office add-ins

The Word editor relies on a DocReview360 Office add-in. Install the add-in in
every environment so the editor can connect to Word:

1. **Local development** – open Word, choose *Insert → Add-ins → Upload My
   Add-in* and select the DocReview360 manifest.
2. **Staging / production** – deploy the same manifest through your Microsoft 365
   admin center or a SharePoint catalog so that all users receive the add-in.
3. **Office Online** – sideload the manifest from the browser's *Add-ins* menu or
   use centralised deployment.

After the add-in is installed, restart Word and the editor will load normally.

## Secret management

DocReview360 resolves service credentials through a simple vault interface. To
configure a vault, add a section to `settings.yaml`:

```yaml
vault:
  url: http://localhost:8200
  token: my-dev-token
```

When configured, provider modules such as the OpenAI and SharePoint clients pull
their tokens from the vault. If no vault is configured, the application falls
back to environment variables like `OPENAI_KEY` or `SHAREPOINT_TOKEN`.

## Role permissions

Role-to-permission mappings are sourced from `settings.yaml`.  See
[`docs/rbac_configuration.md`](./rbac_configuration.md) for guidance on updating
the matrix and using the CLI helpers to inspect or modify roles.

## Documenso circuit breaker

The Documenso connector automatically pauses remote requests after repeated
HTTP failures and falls back to the in-memory stub. Tune the circuit breaker via
environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `DOCUMENSO_FAILURE_THRESHOLD` | `3` | Number of consecutive HTTP errors allowed within the window. |
| `DOCUMENSO_FAILURE_WINDOW_SECONDS` | `60` | Rolling time window used to evaluate failures. |
| `DOCUMENSO_FAILURE_COOLDOWN_SECONDS` | `300` | Duration to wait before attempting to recover the remote integration. |

While the breaker is open the `SIGNATURE_FAILURES` counter exposes the HTTP
failure reason in its `reason` label and `providers.yaml` is updated with
`documenso.healthy: false`. Once the upstream service is stable you can
re-enable Documenso by either editing `providers.yaml` to mark the provider as
healthy or by running the helper below from the project root:

```bash
poetry run python - <<'PY'
from docreview360.provider_store import set_provider_health

set_provider_health("documenso", True)
PY
```

The breaker automatically resets after the cooldown period, but manually
flipping the health flag lets operators restore the remote provider immediately
after verifying that Documenso is back online.

## Responding to audit log corruption alerts

The audit subsystem raises an ``audit_log_corruption_detected`` event whenever a
malformed or tampered entry is encountered. When the event fires DocReview360
automatically replays the SharePoint integrity task and re-hashes the audit log
segments so the append-only anchor store stays in sync. Operators should:

1. Inspect the audit log tail (`tail -n50 src/docreview360/audit.log`) to confirm
   the offending entry.
2. Review the SharePoint verification task result in the worker logs to ensure
   document hashes match expectations.
3. Export the refreshed anchors from ``tamper_proof_store/`` for offline
   comparison if a regulatory review is underway.
4. Open an incident if the corruption originated from an unexpected source or if
   anchors diverge after the automated recovery.
