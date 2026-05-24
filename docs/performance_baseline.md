# Performance Baseline (v0.1)

Measured at (UTC): 2026-05-24T21:04:25.332355Z

## Metrics

- API cold start (TestClient health probe): `2.7981s`
- 50-page document import+load time: `0.0815s`
- Approval state transition latency (pending -> rejected): `0.009s`
- Concurrency (10 simultaneous reviewers): `0.0777s` total, `7.77ms` average transition
- Concurrency (25 simultaneous reviewers): `0.1879s` total, `7.52ms` average transition

## Notes

- This baseline is intended for release transparency, not synthetic peak benchmarking.
- Re-run before each release candidate and record the generated JSON artifact.
