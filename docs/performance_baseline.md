# Performance Baseline (v0.1)

Measured at (UTC): 2026-03-01T19:40:05.564821Z

## Metrics

- API cold start (TestClient health probe): `1.2833s`
- 50-page document import+load time: `0.023s`
- Approval state transition latency (pending -> rejected): `0.0044s`
- Concurrency (10 simultaneous reviewers): `0.0315s` total, `3.15ms` average transition
- Concurrency (25 simultaneous reviewers): `0.0827s` total, `3.31ms` average transition

## Notes

- This baseline is intended for release transparency, not synthetic peak benchmarking.
- Re-run before each release candidate and record the generated JSON artifact.
