# Performance Baseline (v0.1)

Measured at (UTC): 2026-03-15T13:40:08.502059Z

## Metrics

- API cold start (TestClient health probe): `2.1751s`
- 50-page document import+load time: `0.0273s`
- Approval state transition latency (pending -> rejected): `0.0051s`
- Concurrency (10 simultaneous reviewers): `0.043s` total, `4.3ms` average transition
- Concurrency (25 simultaneous reviewers): `0.1032s` total, `4.13ms` average transition

## Notes

- This baseline is intended for release transparency, not synthetic peak benchmarking.
- Re-run before each release candidate and record the generated JSON artifact.
