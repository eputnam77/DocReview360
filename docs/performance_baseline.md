# Performance Baseline (v0.1)

Measured at (UTC): 2026-03-21T21:59:26.828769Z

## Metrics

- API cold start (TestClient health probe): `2.5322s`
- 50-page document import+load time: `0.0471s`
- Approval state transition latency (pending -> rejected): `0.0044s`
- Concurrency (10 simultaneous reviewers): `0.0415s` total, `4.15ms` average transition
- Concurrency (25 simultaneous reviewers): `0.1015s` total, `4.06ms` average transition

## Notes

- This baseline is intended for release transparency, not synthetic peak benchmarking.
- Re-run before each release candidate and record the generated JSON artifact.
