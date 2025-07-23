## Test Run Summary

Lock integrity checks:
- `poetry check --lock` failed with errors.
- `pip-compile --dry-run` succeeded.

Type check failures:
- `mypy src` reported 3 errors (see `/tmp/mypy.log`).

Test results:
- `pytest` aborted with 1 error during collection (see `/tmp/pytest.log`).

No HTML coverage report was generated.

Label: `ready-for:builder`
