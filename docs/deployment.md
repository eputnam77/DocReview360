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

## Deploying the ONNX model

The Docker image bundles ONNX Runtime so you can ship the AI classifier alongside
the API service without extra infrastructure. A typical CPU deployment mounts a
model package created by `docreview360 ml package` and wires the following
variables:

```bash
DOCREVIEW360_ML_MODEL_DIR=/app/artifacts/packages/2024-05-01_120000
DOCREVIEW360_ML_PROVIDER=cpu
DOCREVIEW360_ML_THREADS=$(nproc)
```

The worker detects additional providers when the right libraries are present:

| Provider | Requirement | Notes |
| --- | --- | --- |
| `CUDAExecutionProvider` | NVIDIA drivers + CUDA toolkit | Optional—falls back to CPU when GPU is absent. |
| `CoreMLExecutionProvider` | macOS 13+ with Apple Silicon | Ideal for Apple Silicon dev machines. |
| `OpenVINOExecutionProvider` | Intel OpenVINO runtime | Helps squeeze extra throughput on Xeon hosts. |

If no provider can be initialised, DocReview360 refuses to start and surfaces a
clear error in the worker logs. See **Troubleshooting** below for quick fixes.

## Secret management

DocReview360 resolves service credentials through a simple vault interface and
prefers external secret stores over local files. To configure a vault, add a
section to `settings.yaml`:

```yaml
vault:
  url: http://localhost:8200
  token: my-dev-token
```

When configured, provider modules such as the OpenAI and SharePoint clients pull
their tokens from the vault. If no vault is configured, the application falls
back to environment variables like `OPENAI_KEY` or `SHAREPOINT_TOKEN`.

If you must persist secrets in `settings.yaml`, enable encryption at rest and
include the `secrets` scope so values are stored as `ENC(...)` payloads. On
startup, plaintext legacy secrets are automatically migrated to encrypted
payloads when keys are available:

```yaml
security:
  encryption_at_rest:
    enabled: true
    key_id: encryption-primary
    required_for:
      - secrets
```

This is best used as a bootstrap mechanism for local or single-node installs;
production environments should keep provider credentials in an external vault
or environment variables to avoid storing secrets on disk.

## Encryption at rest configuration

Archive artefacts, archive metadata, and backup payloads can be encrypted at
rest using AES-GCM. Configure the policy in `settings.yaml` and store the key
material in the vault or environment under the same key id:

```yaml
security:
  encryption_at_rest:
    enabled: true
    key_id: encryption-primary
    required_for:
      - archive
      - backup
```

The encryption key must be 16, 24, or 32 bytes (raw or base64 encoded). When
rotating keys, keep the previous key material available under its key id until
all encrypted artefacts and backups have been reprocessed or retired; the
payload header records which key id was used so DocReview360 can decrypt older
data during restore.

## S3 server-side encryption (SSE)

If you store archives, audit log anchors, or backups in S3, you can enable
bucket-side encryption by setting defaults in `settings.yaml`. DocReview360
threads these defaults into every S3 `put_object` call, so callers do not need
to repeat flags:

```yaml
storage:
  s3:
    sse: aws:kms
    kms_key_id: arn:aws:kms:us-east-1:123456789012:key/abc-def
```

Set `sse` to `AES256` to use S3-managed keys, or to `aws:kms` to enforce
customer-managed KMS keys. When using KMS, prefer a dedicated key and ensure
the worker role has `kms:Encrypt` permissions on it. If `kms_key_id` is
configured, DocReview360 will pass it through as `SSEKMSKeyId` with every S3
write.

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

## Troubleshooting inference deployments

### "No suitable execution provider" errors

1. Confirm the ONNX Runtime build supports your architecture. The Docker image
   ships with the CPU build, so GPU providers are disabled unless you replace
   the wheel.
2. Verify that `DOCREVIEW360_ML_PROVIDER` matches one of the providers listed by
   `docreview360 ml info`.
3. Delete stale cached models in `/tmp/docreview360/ml/` if you recently
   switched providers—this forces the runtime to reload the graph.

### Apple Silicon & CPU-only environments

- Prefer the `CoreMLExecutionProvider` locally (`DOCREVIEW360_ML_PROVIDER=coreml`),
  but leave production to `cpu` unless you are building a macOS-only stack.
- Install the [onnxruntime-silicon](https://pypi.org/project/onnxruntime-silicon/)
  wheel when developing outside Docker; it bundles ARM64 optimisations.
- Skip GPU-only quantisation modes. Both dynamic and static INT8 pipelines run
  entirely on CPUs and keep parity with x86 servers.
- Use `docreview360 ml export --opset 18 --quantize dynamic` to ship a single
  artifact that behaves consistently across Intel, AMD, and Apple chips.

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
