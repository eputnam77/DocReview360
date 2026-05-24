# Performance Baseline (v0.1)

Measured at (UTC): 2026-05-24T13:29:52.972699Z

## Metrics

- API cold start (TestClient health probe): `1.7766s`
- 50-page document import+load time: `0.0304s`
- Approval state transition latency (pending -> rejected): `0.0071s`
- Concurrency (10 simultaneous reviewers): `0.0801s` total, `8.01ms` average transition
- Concurrency (25 simultaneous reviewers): `0.1757s` total, `7.03ms` average transition

## Notes

- This baseline is intended for release transparency, not synthetic peak benchmarking.
- Re-run before each release candidate and record the generated JSON artifact.
