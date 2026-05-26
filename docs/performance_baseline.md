# Performance Baseline (v0.1)

Measured at (UTC): 2026-05-26T10:45:12.829489Z

## Metrics

- API cold start (TestClient health probe): `1.8683s`
- 50-page document import+load time: `0.0319s`
- Approval state transition latency (pending -> rejected): `0.0058s`
- Concurrency (10 simultaneous reviewers): `0.0562s` total, `5.62ms` average transition
- Concurrency (25 simultaneous reviewers): `0.1452s` total, `5.81ms` average transition

## Notes

- This baseline is intended for release transparency, not synthetic peak benchmarking.
- Re-run before each release candidate and record the generated JSON artifact.
