# Settings reference

`settings.yaml` holds runtime configuration and is loaded at startup. This page describes the keys that matter, their defaults, and what you must change before production.

Environment variables override `settings.yaml`. Set secrets there, not in the file.

## Override these before production

Three defaults are unsafe outside development.

| Key | Default | Why it matters | What to do |
| --- | --- | --- | --- |
| `secrets.encryption-primary` | Placeholder key | A demo key protects nothing at rest | Generate a unique 32-byte key. Store it in a vault or environment variable. Never commit real key material. |
| `notifications.slack_webhook_url` | `https://hooks.slack.com/test123` | Notifications go to the wrong channel | Replace with your webhook URL, or remove the key. |
| `signature_provider_primary` | `sandbox` | Sandbox signatures are not legally binding | Set to `documenso` or another provider. |

Also confirm `DOCREVIEW360_ENV` is **not** set to `dev` or `test` in production. Those values seed the demo accounts `alice/password` and `bob/password`.

## Defaults you can keep

| Key | Default | Notes |
| --- | --- | --- |
| `audit_log.retention_days` | `2555` (~7 years) | Suitable for federal compliance. Reduce only if your regulations allow. |
| `audit_log.purge_interval_minutes` | `1440` (daily) | Adjust to match your operational cadence. |
| `security.encryption_at_rest.enabled` | `true` | Leave on in production. |
| `security.encryption_at_rest.required_for` | `[archive, backup]` | Add `secrets` for broader coverage. |
| `signature_verification.interval_minutes` | `60` | Polling interval for re-verification. |
| `signature_verification.scope` | `approved` | Only approved documents are re-verified. |
| `notifications.email_enabled` | `false` | Configure SMTP before enabling. |
| `notifications.teams_enabled` | `false` | Microsoft Teams notifications are off. |
| `fsv_check_categories.*` | Mixed | Review which style checks match your requirements. |

## Environment variable overrides

These take precedence over `settings.yaml`. Set them in your deployment platform.

| Variable | Purpose |
| --- | --- |
| `DOCREVIEW360_ENV` | Set to `production` to enforce secret validation and disable demo seeding. |
| `DOCREVIEW360_SECRET_KEY` | JWT signing secret. Must be strong and random in production. |
| `DOCREVIEW360_DATABASE_URL` | Database connection string. |
| `SIGNATURE_PROVIDER` | Overrides `signature_provider_primary`. |
| `DOCREVIEW360_ML_MODEL_DIR` | Path to the packaged ONNX model directory. |
| `OPENAI_KEY` | OpenAI API token, when no vault is configured. |
| `SHAREPOINT_TOKEN` | SharePoint bearer token, when no vault is configured. |

For the complete list, see [Environment variables](environment_variables.md).

## Avoid these

- Committing a `settings.yaml` that contains real encryption keys, webhook URLs, or API tokens.
- Leaving `signature_provider_primary: sandbox` in production.
- Disabling `security.encryption_at_rest.enabled` where you handle regulated documents.
- Setting `DOCREVIEW360_ENV=dev` in production, which seeds demo accounts with known passwords.

## Related pages

- [Environment variables](environment_variables.md)
- [RBAC configuration](rbac_configuration.md)
- [Key rotation](security/key-rotation.md)
- [Data retention and deletion](data_retention_and_deletion.md)
