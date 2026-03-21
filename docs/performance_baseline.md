# Performance Baseline (v0.1)

Measured at (UTC): 2026-03-21T12:32:32.817902Z

## Metrics

- API cold start (TestClient health probe): `2.2754s`
- 50-page document import+load time: `0.0503s`
- Approval state transition latency (pending -> rejected): `0.0061s`
- Concurrency (10 simultaneous reviewers): `0.0515s` total, `5.15ms` average transition
- Concurrency (25 simultaneous reviewers): `0.1578s` total, `6.31ms` average transition

## Notes

- This baseline is intended for release transparency, not synthetic peak benchmarking.
- Re-run before each release candidate and record the generated JSON artifact.
