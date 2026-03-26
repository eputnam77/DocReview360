# Performance Baseline (v0.1)

Measured at (UTC): 2026-03-26T15:05:03.767200Z

## Metrics

- API cold start (TestClient health probe): `2.166s`
- 50-page document import+load time: `0.0501s`
- Approval state transition latency (pending -> rejected): `0.0038s`
- Concurrency (10 simultaneous reviewers): `0.0339s` total, `3.39ms` average transition
- Concurrency (25 simultaneous reviewers): `0.0946s` total, `3.79ms` average transition

## Notes

- This baseline is intended for release transparency, not synthetic peak benchmarking.
- Re-run before each release candidate and record the generated JSON artifact.
