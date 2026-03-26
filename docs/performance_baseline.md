# Performance Baseline (v0.1)

Measured at (UTC): 2026-03-26T01:21:25.514901Z

## Metrics

- API cold start (TestClient health probe): `2.3442s`
- 50-page document import+load time: `0.0251s`
- Approval state transition latency (pending -> rejected): `0.0048s`
- Concurrency (10 simultaneous reviewers): `0.0398s` total, `3.98ms` average transition
- Concurrency (25 simultaneous reviewers): `0.1018s` total, `4.07ms` average transition

## Notes

- This baseline is intended for release transparency, not synthetic peak benchmarking.
- Re-run before each release candidate and record the generated JSON artifact.
