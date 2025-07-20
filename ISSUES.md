## Test Run Summary

Lock integrity checks failed:
- `poetry lock --check` reported: *The option "--check" does not exist*.
- `npm ci --dry-run` failed because no `package-lock.json` was present at repo root.
- `cargo check --locked` failed due to missing `Cargo.lock`.

Type checks failed:
- `mypy src/docreview360` error: missing plugin `pydantic`.
- `npx tsc --noEmit` produced numerous errors because dependencies were not installed.
- `cargo clippy` not installed for current toolchain.

Test suite failed to start:
- `pytest` could not recognize coverage options, indicating `pytest-cov` missing.

No coverage report was generated.
