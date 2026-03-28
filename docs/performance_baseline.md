# Performance Baseline (v0.1)

Measured at (UTC): 2026-03-28T22:04:16.522914Z

## Metrics

- API cold start (TestClient health probe): `2.7248s`
- 50-page document import+load time: `0.0536s`
- Approval state transition latency (pending -> rejected): `0.0062s`
- Concurrency (10 simultaneous reviewers): `0.0706s` total, `7.06ms` average transition
- Concurrency (25 simultaneous reviewers): `0.1951s` total, `7.8ms` average transition

## Notes

- This baseline is intended for release transparency, not synthetic peak benchmarking.
- Re-run before each release candidate and record the generated JSON artifact.
