import pytest
from docreview360.metadata import normalize_description


def test_normalize_description_strips_whitespace():
    assert normalize_description('  hello   world ') == 'hello world'


def test_normalize_description_empty_raises():
    with pytest.raises(ValueError):
        normalize_description('   \n\t')
