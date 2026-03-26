# Performance Baseline (v0.1)

Measured at (UTC): 2026-03-26T00:42:29.378640Z

## Metrics

- API cold start (TestClient health probe): `1.5617s`
- 50-page document import+load time: `0.0205s`
- Approval state transition latency (pending -> rejected): `0.0037s`
- Concurrency (10 simultaneous reviewers): `0.0309s` total, `3.09ms` average transition
- Concurrency (25 simultaneous reviewers): `0.0812s` total, `3.25ms` average transition

## Notes

- This baseline is intended for release transparency, not synthetic peak benchmarking.
- Re-run before each release candidate and record the generated JSON artifact.
