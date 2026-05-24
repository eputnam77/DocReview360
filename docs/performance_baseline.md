# Performance Baseline (v0.1)

Measured at (UTC): 2026-05-24T18:31:59.756173Z

## Metrics

- API cold start (TestClient health probe): `1.7633s`
- 50-page document import+load time: `0.0307s`
- Approval state transition latency (pending -> rejected): `0.0062s`
- Concurrency (10 simultaneous reviewers): `0.0638s` total, `6.38ms` average transition
- Concurrency (25 simultaneous reviewers): `0.1608s` total, `6.43ms` average transition

## Notes

- This baseline is intended for release transparency, not synthetic peak benchmarking.
- Re-run before each release candidate and record the generated JSON artifact.
