import importlib
import sys

import pytest

import docreview360 as dr


def test_placeholder_basic() -> None:
    assert dr.placeholder(2) == 84


def test_placeholder_negative() -> None:
    with pytest.raises(ValueError):
        dr.placeholder(-1)


def test_placeholder_type_error() -> None:
    with pytest.raises(TypeError):
        dr.placeholder("3")


def test_placeholder_bool_rejected() -> None:
    """Booleans should not be treated as integers."""
    with pytest.raises(TypeError):
        dr.placeholder(True)


def test_lazy_import_watchlist() -> None:
    import docreview360

    sys.modules.pop("docreview360.watchlist", None)
    docreview360.__dict__.pop("watchlist", None)
    importlib.reload(docreview360)
    assert "watchlist" not in docreview360.__dict__
    module = docreview360.watchlist
    assert module is docreview360.watchlist
