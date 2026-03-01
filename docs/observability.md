# Observability Standard (v0.1)

This document defines DocReview360 operational logging and monitoring expectations for production deployments.

## 1. Structured JSON Logging

- Production mode emits structured JSON log events from `docreview360.logs.log_event`.
- Structured logs are enabled when either:
  - `DOCREVIEW360_ENV` is `production`, `prod`, or `staging`, or
  - `DOCREVIEW360_LOG_FORMAT=json`, or
  - `DOCREVIEW360_STRUCTURED_LOGS=true`.
- Log payload fields include: `id`, `timestamp`, `action`, `severity`, `user_id`, `entity_type`, `entity_id`, `ip_address`, and `details`.

## 2. Correlation IDs (Request Tracing)

- Every HTTP request is assigned a correlation ID via API middleware.
- Incoming headers supported:
  - `X-Correlation-ID` (preferred)
  - `X-Request-ID` (fallback)
- If no header is provided, DocReview360 generates a UUID.
- Response header always includes `X-Correlation-ID`.
- The correlation ID is propagated to log entries via `trace_id` in log `details`.

## 3. Severity Levels and Error Taxonomy

### Severity levels

- `info`
- `warning`
- `error`

Aliases are normalized (`warn` -> `warning`, `err`/`fatal` -> `error`). Unknown levels default to `info`.

### Error taxonomy

For `error` severity events, `details.error_code` is normalized to one of:

- `auth_error`
- `compliance_error`
- `configuration_error`
- `data_integrity_error`
- `dependency_error`
- `permission_error`
- `rate_limit_error`
- `system_error`
- `validation_error`

If no valid `error_code` is supplied for an error event, `system_error` is used.

## 4. Sensitive Field Redaction

Log payloads are redacted by default for sensitive keys, including:

- `password`
- `token`
- `access_token`
- `secret`
- `api_key`
- `authorization`
- `cookie`
- `session`
- `csrf`
- `key`

Nested dictionaries/lists are redacted recursively.

## 5. Recommended Monitoring Stack and Minimum Alerts

### Recommended stack

- Metrics: Prometheus (`/metrics` endpoint)
- Logs: structured JSON to stdout -> collector (Loki, CloudWatch, Elastic, or equivalent)
- Dashboards: Grafana (or provider-native dashboard)
- Error tracking: Sentry (optional)

### Minimum production alerts

- API health check failing (`/health` non-200 or timeout)
- Sustained 5xx error rate above baseline
- Authentication failure spikes / lockout spikes
- Signature verification failure spikes
- Worker task failure spikes
- Database connectivity failures
- Log ingestion pipeline stalled or dropping events
