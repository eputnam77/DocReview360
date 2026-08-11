# Environment variables

Use environment variables to override file-based configuration at runtime. This is how you pass secrets and deployment-specific settings.

## Precedence

Configuration resolves in this order:

1. Environment variables
2. `docreview360.yaml`
3. `settings.yaml`
4. Application defaults

## Minimum local setup

For local development, these two are usually enough:

```bash
DOCREVIEW360_ENV=dev
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
```

Set `NEXT_PUBLIC_API_BASE` in `frontend/.env.local`, and browse the frontend on the same hostname you put in that URL. The session cookie is host-scoped, so serving the frontend at `localhost` while the API is at `127.0.0.1` signs you out on every page load.

## Set these in production

Set `DOCREVIEW360_ENV` to any value other than `dev` or `test`, and DocReview360 refuses to start with missing secrets rather than falling back to development defaults. Provide at least:

| Variable | Why |
| --- | --- |
| `DOCREVIEW360_ENV` | Enforces secret validation and stops demo-user seeding. |
| `DOCREVIEW360_SECRET_KEY` | Signs API tokens. Anyone with this value can mint valid tokens. |
| `DOCREVIEW360_OIDC_SECRET_KEY` | Signs OIDC tokens. |
| `DOCREVIEW360_DATABASE_URL` | Points at your production database instead of local SQLite. |
| `DOCREVIEW360_ALLOW_ORIGINS` | Restricts CORS to your own frontend origins. |
| `DOCREVIEW360_SIGNATURE_SECRET` | Required for signature verification. |

Never set `DOCREVIEW360_SEED_DEMO_USERS=true` in production. It creates accounts with published passwords.

## Authentication and tokens

| Variable | Default | Purpose |
| --- | --- | --- |
| `DOCREVIEW360_ENV` | empty | Environment name. Non-dev and non-test values enforce required secrets. |
| `DOCREVIEW360_SECRET_KEY` | generated dev secret | JWT signing key for API tokens. |
| `DOCREVIEW360_ALGORITHM` | `HS256` | JWT signing algorithm. |
| `DOCREVIEW360_ACCESS_EXPIRE_MINUTES` | `30` | Access token TTL in minutes. |
| `DOCREVIEW360_REFRESH_EXPIRE_DAYS` | `30` | Refresh token TTL in days. |
| `DOCREVIEW360_TOKEN_ISSUER` | `docreview360.local` | JWT issuer for API tokens. |
| `DOCREVIEW360_TOKEN_AUDIENCE` | `docreview360-users` | JWT audience for API tokens. |
| `DOCREVIEW360_OIDC_SECRET_KEY` | generated dev secret | JWT signing key for OIDC tokens. |
| `DOCREVIEW360_OIDC_ALGORITHM` | `HS256` | OIDC JWT signing algorithm. |
| `DOCREVIEW360_OIDC_EXPIRE_MINUTES` | `30` | OIDC token TTL in minutes. |
| `DOCREVIEW360_OIDC_TOKEN_ISSUER` | `docreview360-oidc.local` | OIDC issuer. |
| `DOCREVIEW360_OIDC_TOKEN_AUDIENCE` | `docreview360-oidc` | OIDC audience. |
| `DOCREVIEW360_REQUIRE_MFA` | `false` | Require OTP for login when true. |
| `DOCREVIEW360_SEED_DEMO_USERS` | `true` | Seed demo users in local and test environments. |
| `DOCREVIEW360_MAX_FAILED_ATTEMPTS` | `5` | Failed logins allowed before lockout. |
| `DOCREVIEW360_LOCKOUT_SECONDS` | `300` | Lockout period in seconds. |
| `DOCREVIEW360_USER_DB` | `./docreview360_users.db` | SQLite database path for users. |

## Database and storage

| Variable | Default | Purpose |
| --- | --- | --- |
| `DOCREVIEW360_DATABASE_URL` | internal SQLite default | SQLAlchemy database URL for app data and audit logs. |
| `DOCREVIEW360_RBAC_DB` | `docreview360_roles.db` | SQLite database path for RBAC state. |
| `DOCREVIEW360_SEARCH_DB` | `search_state.db` | SQLite database path for saved searches. |
| `DOCREVIEW360_ARCHIVE_BUCKET` | `archive_store` | Directory for archived artifacts. |
| `DOCREVIEW360_SAMPLE_DIR` | `samples` | Directory for sample documents. |
| `DOCREVIEW360_DATA_DIR` | unset | Base directory for data files. |
| `DOCREVIEW360_TEMPLATE_STORE_FILE` | `template_store.json` | Template metadata store file. |
| `DOCREVIEW360_TEMPLATES_DIR` | `templates/golden` | Template file directory. |
| `DOCREVIEW360_SETTINGS_FILE` | `settings.yaml` | Settings file path. |
| `DOCREVIEW360_CONFIG_FILE` | `docreview360.yaml` | Main config file path. |
| `DOCREVIEW360_ENVIRONMENTS_FILE` | `environments.yaml` | Multi-environment config file path. |
| `DOCREVIEW360_WORKER_STATE` | `worker_state.json` | Worker coordination state file. |

## API and frontend

| Variable | Default | Purpose |
| --- | --- | --- |
| `DOCREVIEW360_ALLOW_ORIGINS` | unset | Comma-separated list of allowed CORS origins. |
| `DOCREVIEW360_RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate-limit window in seconds. |
| `DOCREVIEW360_TOKEN_RATE_LIMIT` | `20` | Token endpoint requests per window. |
| `DOCREVIEW360_LOGIN_RATE_LIMIT` | `20` | Login requests per window. |
| `DOCREVIEW360_UPLOAD_RATE_LIMIT` | `30` | Upload requests per window. |
| `NEXT_PUBLIC_API_BASE` | unset | Frontend API base URL. Leave blank to use the dashboard host. |

## Signatures and integrations

| Variable | Default | Purpose |
| --- | --- | --- |
| `DOCREVIEW360_SIGNATURE_SECRET` | unset | HMAC secret for signature verification. |
| `DOCREVIEW360_ALLOW_SIGNATURE_FALLBACK` | unset | Allow fallback signature verification. |
| `SIGNATURE_PROVIDER` | `sandbox` | Primary signature provider. |
| `SIGNATURE_PROVIDER_PRIMARY` | unset | Explicit primary provider override. |
| `SIGNATURE_PROVIDER_FALLBACK` | unset | Comma-separated fallback providers. |
| `DOCREVIEW360_SHAREPOINT_TIMEOUT_SECONDS` | unset | SharePoint timeout override. |

## Feature flags

| Variable | Default | Purpose |
| --- | --- | --- |
| `DOCREVIEW360_ENABLE_TEMPLATE_PERSISTENCE` | unset | Persist template edits to the template store file. |
| `DOCREVIEW360_ENABLE_EMAIL_TEMPLATE_PERSISTENCE` | unset | Persist email template edits. |
| `DOCREVIEW360_ENABLE_WORKFLOW_TEMPLATE_PERSISTENCE` | unset | Persist workflow template edits. |
| `DOCREVIEW360_SKIP_SAMPLE_BOOTSTRAP` | unset | Skip seeding sample data when set. |
| `DOCREVIEW360_ENABLE_SAMPLE_BOOTSTRAP` | unset | Re-enable sample bootstrap when set to `1`. |

## ML and AI

| Variable | Default | Purpose |
| --- | --- | --- |
| `DOCREVIEW360_ML_MODEL_DIR` | unset | Path to packaged ONNX artifacts. |
| `DOCREVIEW360_ML_PROVIDER` | `cpu` | ONNX runtime provider. |
| `DOCREVIEW360_ML_THREADS` | unset | Thread count for ONNX runtime. |

## E2E

| Variable | Default | Purpose |
| --- | --- | --- |
| `DOCREVIEW360_E2E_MODE` | unset | Enable E2E-specific behavior when set to `1`. |

## Example local setup

Unix or macOS:

```bash
export DOCREVIEW360_ENV=dev
export NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
```

Windows PowerShell:

```powershell
$env:DOCREVIEW360_ENV="dev"
$env:NEXT_PUBLIC_API_BASE="http://127.0.0.1:8000"
```

## Related pages

- [Get started](getting_started.md)
- [Settings reference](settings.md)
- [Deployment](deployment.md)
- [Testing and quality](testing_and_quality.md)
