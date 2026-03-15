# Performance Baseline (v0.1)

Measured at (UTC): 2026-03-15T00:19:43.777489Z

## Metrics

- API cold start (TestClient health probe): `1.4537s`
- 50-page document import+load time: `0.0287s`
- Approval state transition latency (pending -> rejected): `0.0058s`
- Concurrency (10 simultaneous reviewers): `0.0556s` total, `5.56ms` average transition
- Concurrency (25 simultaneous reviewers): `0.135s` total, `5.4ms` average transition

## Notes

- This baseline is intended for release transparency, not synthetic peak benchmarking.
- Re-run before each release candidate and record the generated JSON artifact.
