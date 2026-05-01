# Performance Baseline (v0.1)

Measured at (UTC): 2026-05-01T16:20:50.724288Z

## Metrics

- API cold start (TestClient health probe): `3.9454s`
- 50-page document import+load time: `0.0852s`
- Approval state transition latency (pending -> rejected): `0.0113s`
- Concurrency (10 simultaneous reviewers): `0.0802s` total, `8.02ms` average transition
- Concurrency (25 simultaneous reviewers): `0.2608s` total, `10.43ms` average transition

## Notes

- This baseline is intended for release transparency, not synthetic peak benchmarking.
- Re-run before each release candidate and record the generated JSON artifact.
