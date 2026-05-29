from docreview360.api import _fail_on_startup_validator_error


def test_unexpected_startup_validator_errors_fail_closed_in_production() -> None:
    assert _fail_on_startup_validator_error("production") is True
    assert _fail_on_startup_validator_error("staging") is True


def test_unexpected_startup_validator_errors_are_nonfatal_in_dev() -> None:
    assert _fail_on_startup_validator_error("dev") is False
    assert _fail_on_startup_validator_error("test") is False
