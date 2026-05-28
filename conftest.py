"""Repository-wide pytest preflight checks."""

from __future__ import annotations

import pytest

from pytest_preflight import validate_test_environment


def pytest_configure(config: pytest.Config) -> None:
    """Validate the runner before pytest starts importing application tests."""

    validate_test_environment()
