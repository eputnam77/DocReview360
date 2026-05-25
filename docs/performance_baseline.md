# Performance Baseline (v0.1)

Measured at (UTC): 2026-05-25T14:00:04.707162Z

## Metrics

- API cold start (TestClient health probe): `1.7346s`
- 50-page document import+load time: `0.0342s`
- Approval state transition latency (pending -> rejected): `0.0098s`
- Concurrency (10 simultaneous reviewers): `0.0846s` total, `8.46ms` average transition
- Concurrency (25 simultaneous reviewers): `0.2258s` total, `9.03ms` average transition

## Notes

- This baseline is intended for release transparency, not synthetic peak benchmarking.
- Re-run before each release candidate and record the generated JSON artifact.
