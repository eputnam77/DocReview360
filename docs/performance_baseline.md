# Performance Baseline (v0.1)

Measured at (UTC): 2026-05-01T16:49:37.598320Z

## Metrics

- API cold start (TestClient health probe): `3.1256s`
- 50-page document import+load time: `0.0555s`
- Approval state transition latency (pending -> rejected): `0.0092s`
- Concurrency (10 simultaneous reviewers): `0.0827s` total, `8.27ms` average transition
- Concurrency (25 simultaneous reviewers): `0.2438s` total, `9.75ms` average transition

## Notes

- This baseline is intended for release transparency, not synthetic peak benchmarking.
- Re-run before each release candidate and record the generated JSON artifact.
