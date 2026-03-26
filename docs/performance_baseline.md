# Performance Baseline (v0.1)

Measured at (UTC): 2026-03-26T10:51:26.799415Z

## Metrics

- API cold start (TestClient health probe): `2.2521s`
- 50-page document import+load time: `0.0293s`
- Approval state transition latency (pending -> rejected): `0.0053s`
- Concurrency (10 simultaneous reviewers): `0.0487s` total, `4.87ms` average transition
- Concurrency (25 simultaneous reviewers): `0.1081s` total, `4.33ms` average transition

## Notes

- This baseline is intended for release transparency, not synthetic peak benchmarking.
- Re-run before each release candidate and record the generated JSON artifact.
