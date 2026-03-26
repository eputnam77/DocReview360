# settings.yaml — Production-Safe Configuration Reference

`settings.yaml` is loaded at startup and stores runtime configuration for
DocReview360. This document describes each significant key, its safe default,
and flags values that **operators must override** before going to production.

---

## Required overrides before production

| Key | Default in settings.yaml | Risk | Action required |
|-----|--------------------------|------|-----------------|
| `secrets.encryption-primary` | Base64-encoded placeholder key | Weak/demo key — protects data at rest | **Generate a unique 32-byte key** and store it in a vault or environment variable; never commit real key material to source control. |
| `notifications.slack_webhook_url` | `https://hooks.slack.com/test123` | Hardcoded test webhook — leaks notifications to wrong channel | Replace with your real Slack webhook URL or remove the key. |
| `signature_provider_primary` | `sandbox` | Signatures are not legally binding in sandbox mode | Set to `documenso` (or another provider) for production signing. |

---

## Safe defaults (no action required)

| Key | Default | Notes |
|-----|---------|-------|
| `audit_log.retention_days` | `2555` (~7 years) | Appropriate for federal compliance. Reduce only if regulations permit. |
| `audit_log.purge_interval_minutes` | `1440` (daily) | Safe. Adjust to match your operational cadence. |
| `security.encryption_at_rest.enabled` | `true` | Encryption is on by default. Do not disable in production. |
| `security.encryption_at_rest.required_for` | `[archive, backup]` | Ensures archive and backup payloads are encrypted. Extend to include `secrets` for additional protection. |
| `signature_verification.interval_minutes` | `60` | Reasonable polling interval. |
| `signature_verification.scope` | `approved` | Only re-verifies approved documents. |
| `notifications.email_enabled` | `false` | Email notifications are off by default. Configure SMTP before enabling. |
| `notifications.teams_enabled` | `false` | Microsoft Teams notifications are off by default. |
| `fsv_check_categories.*` | Mixed | Review enabled checks match your style requirements. |

---

## Environment variables that override settings.yaml

The following environment variables take precedence over `settings.yaml` values.
Set them in your deployment platform rather than storing credentials in the file.

| Variable | Purpose |
|----------|---------|
| `DOCREVIEW360_ENV` | Set to `production` to enforce secret validation and disable demo seeding. |
| `SIGNATURE_PROVIDER` | Overrides `signature_provider_primary` (`sandbox` or `documenso`). |
| `DOCREVIEW360_ML_MODEL_DIR` | Path to the packaged ONNX model directory. |
| `DOCREVIEW360_DATABASE_URL` | Database connection string (SQLite path or Postgres URL). |
| `DOCREVIEW360_SECRET_KEY` | JWT signing secret — must be a strong random value in production. |
| `OPENAI_KEY` | OpenAI API token (used when no vault is configured). |
| `SHAREPOINT_TOKEN` | SharePoint bearer token (used when no vault is configured). |

---

## Unsafe patterns to avoid

- Do **not** commit a `settings.yaml` that contains real encryption keys,
  webhook URLs, or API tokens to source control.
- Do **not** leave `signature_provider_primary: sandbox` in production; sandbox
  signatures are not legally binding.
- Do **not** disable `security.encryption_at_rest.enabled` in production
  environments that handle regulated documents.
- The demo credentials (`alice/password`, `bob/password`) are seeded only when
  `DOCREVIEW360_ENV=dev`. Ensure this variable is **not** set in production.
