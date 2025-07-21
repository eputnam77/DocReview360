## Test Run Summary

Lock integrity checks:
- `poetry check --lock` succeeded with warnings.
- `pip-compile --dry-run` succeeded.

Type check failures:
- `mypy src tests` reported 76 errors (see `/tmp/mypy.log`).

Test results:
- `pytest` ran 197 tests with 2 skipped but coverage reports were not produced.

No HTML coverage report was generated.

Label: `ready-for:builder`
