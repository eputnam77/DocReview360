# Test Determinism Standard

This guide defines how DocReview360 keeps tests reproducible across machines and time zones.

## Deterministic Time Handling

- The E2E runner (`scripts/run_e2e.py`) generates run IDs in UTC.
- CI sets explicit `E2E_RUN_ID` values (`e2e-smoke`, `e2e-full`) so artifact paths are stable.
- Unit tests for the E2E runner freeze the timestamp source to verify deterministic formatting.

## Time Zone Compatibility

CI runs determinism checks in at least two zones:

- `TZ=UTC`
- `TZ=America/Los_Angeles`

This catches hidden assumptions about local machine time.

## Local Machine State Isolation

- Shared pytest fixtures (`tests/conftest.py`) isolate mutable stores into temporary paths.
- Determinism tests verify explicit environment overrides (`E2E_RUN_ID`, `E2E_RUN_DIR`) are honored.
- Tests should avoid relying on ambient local files, host-specific absolute paths, or system clock formatting.

## Practical Rules for New Tests

- Prefer explicit temp directories (`tmp_path` / `tmp_path_factory`).
- Avoid `datetime.now()` in assertions unless the clock is frozen or the value is normalized.
- Use UTC for persisted timestamps and release artifacts.
- Use stable IDs in tests where ordering or equality matters.
